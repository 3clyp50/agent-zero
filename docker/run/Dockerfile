# Use the latest slim version of Debian
FROM debian:bookworm-slim

# Check if the argument is provided, else throw an error
ARG GIT_REPOSITORY
RUN if [ -z "$GIT_REPOSITORY" ]; then echo "ERROR: GIT_REPOSITORY is not set!" >&2; exit 1; fi
ENV GIT_REPOSITORY=$GIT_REPOSITORY

ARG BRANCH
RUN if [ -z "$BRANCH" ]; then echo "ERROR: BRANCH is not set!" >&2; exit 1; fi
ENV BRANCH=$BRANCH

# Copy contents of the project to /
COPY ./fs/ /

# Pre-installation steps
RUN bash /ins/pre_install.sh $BRANCH

# Install additional software
RUN bash /ins/install_additional.sh $BRANCH

# Install A0
RUN bash /ins/install_A0.sh $GIT_REPOSITORY $BRANCH

# Install desktop sharing components
RUN bash /ins/install_desktop.sh

# Cleanup repo and install A02 without caching, this speeds up builds
ARG CACHE_DATE=none
RUN echo "cache buster $CACHE_DATE" && bash /ins/install_A02.sh $GIT_REPOSITORY $BRANCH

# Post-installation steps
RUN bash /ins/post_install.sh

# Set environment variables for the virtual X server
ENV DISPLAY=:99

# Expose necessary ports
EXPOSE 22 80

# Initialize runtime with Xvfb, Openbox, VNC server, and your existing initialization script
CMD ["/bin/bash", "-c", "/bin/bash /exe/initialize.sh"]
