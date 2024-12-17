from functools import wraps
import threading
from flask import Flask, request, Response
from flask_basicauth import BasicAuth
from flasgger import Swagger
from python.helpers import errors, files, git
from python.helpers.files import get_abs_path
from python.helpers import persist_chat, runtime, dotenv, process
from python.helpers.cloudflare_tunnel import CloudflareTunnel
from python.helpers.extract_tools import load_classes_from_folder
from python.helpers.api import ApiHandler
from python.helpers.print_style import PrintStyle

# Initialize the internal Flask server
app = Flask("app", static_folder=get_abs_path("./webui"), static_url_path="/")
app.config["JSON_SORT_KEYS"] = False  # Disable key sorting in jsonify

lock = threading.Lock()

# Set up basic authentication
basic_auth = BasicAuth(app)


# Require authentication for handlers
def requires_auth(f):
    @wraps(f)
    async def decorated(*args, **kwargs):
        user = dotenv.get_dotenv_value("AUTH_LOGIN")
        password = dotenv.get_dotenv_value("AUTH_PASSWORD")
        if user and password:
            auth = request.authorization
            if not auth or not (auth.username == user and auth.password == password):
                return Response(
                    "Could not verify your access level for that URL.\n"
                    "You have to login with proper credentials",
                    401,
                    {"WWW-Authenticate": 'Basic realm="Login Required"'},
                )
        return await f(*args, **kwargs)

    return decorated


# Handle default address, load index
@app.route("/", methods=["GET"])
@requires_auth
async def serve_index():
    """
    Serve the Index Page
    ---
    get:
      description: Serve the main index page of the web UI.
      responses:
        200:
          description: Returns the index HTML page.
          content:
            text/html:
              schema:
                type: string
    """
    gitinfo = git.get_git_info()
    return files.read_file(
        "./webui/index.html",
        version_no=gitinfo["version"],
        version_time=gitinfo["commit_time"],
    )


def register_api_handler(app, handler: type[ApiHandler]):
    name = handler.__module__.split(".")[-1]
    instance = handler(app, lock)

    docstring = instance.get_docstring()
    http_method = instance.get_supported_http_method()  # Get HTTP methods from handler

    async def handle_request():
        """
        Attach the handler's docstring here.
        """
        return await instance.handle_request(request=request)

    # Assign the docstring to the handle_request function
    handle_request.__doc__ = docstring

    app.add_url_rule(
        f"/{name}",
        f"/{name}",
        handle_request,
        methods=[http_method],  # Use dynamic methods
    )

    PrintStyle().print(f"Registered dynamic route: /{name} with methods {http_method}")


def run():
    PrintStyle().print("Initializing framework...")

    # Suppress request logs
    from werkzeug.serving import WSGIRequestHandler, make_server

    class NoRequestLoggingWSGIRequestHandler(WSGIRequestHandler):
        def log_request(self, code="-", size="-"):
            pass  # Override to suppress request logging

    # Get configuration from environment
    port = (
        runtime.get_arg("port")
        or int(dotenv.get_dotenv_value("WEB_UI_PORT", 0))
        or 5000
    )
    host = (
        runtime.get_arg("host") or dotenv.get_dotenv_value("WEB_UI_HOST") or "localhost"
    )
    use_cloudflare = (
        runtime.get_arg("cloudflare_tunnel")
        or dotenv.get_dotenv_value("USE_CLOUDFLARE", "false").lower()
    ) == "true"

    tunnel = None

    try:
        # Initialize and start Cloudflare tunnel if enabled
        if use_cloudflare and port:
            try:
                tunnel = CloudflareTunnel(port)
                tunnel.start()
            except Exception as e:
                PrintStyle().error(f"Failed to start Cloudflare tunnel: {e}")
                PrintStyle().print("Continuing without tunnel...")

        # Initialize contexts from persisted chats
        persist_chat.load_tmp_chats()

        # Initialize and register API handlers
        handlers = load_classes_from_folder("python/api", "*.py", ApiHandler)
        for handler in handlers:
            register_api_handler(app, handler)

    except Exception as e:
        PrintStyle().error(errors.format_error(e))

    # Initialize Flasgger after all routes have been registered
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": "apispec",
                "route": "/apispec.json",
                "rule_filter": lambda rule: not rule.rule.startswith(
                    "/static"
                ),  # Exclude static routes
                "model_filter": lambda tag: True,  # all in
            }
        ],
        "swagger_ui": True,
        "specs_route": "/docs",
        "title": "My Flask API",
        "description": "This is the API documentation for my Flask server.",
        "version": "1.0.0",
    }

    Swagger(app, config=swagger_config)

    server = None

    try:
        server = make_server(
            host=host,
            port=port,
            app=app,
            request_handler=NoRequestLoggingWSGIRequestHandler,
            threaded=True,
        )
        process.set_server(server)
        server.log_startup()
        server.serve_forever()
    finally:
        # Clean up tunnel if it was started
        if tunnel:
            tunnel.stop()


# Run the internal server
if __name__ == "__main__":
    runtime.initialize()
    dotenv.load_dotenv()
    run()
