import type { ForgeConfig } from '@electron-forge/shared-types';
import { MakerSquirrel } from '@electron-forge/maker-squirrel';
import { MakerZIP } from '@electron-forge/maker-zip';
import { MakerDeb } from '@electron-forge/maker-deb';
import { MakerRpm } from '@electron-forge/maker-rpm';
import { AutoUnpackNativesPlugin } from '@electron-forge/plugin-auto-unpack-natives';
import { WebpackPlugin } from '@electron-forge/plugin-webpack';
import { FusesPlugin } from '@electron-forge/plugin-fuses';
import { FuseV1Options, FuseVersion } from '@electron/fuses';

import { mainConfig } from './webpack.main.config';
import { rendererConfig } from './webpack.renderer.config';

const isStart = process.env.npm_lifecycle_event === 'start';

const config: ForgeConfig = {
  packagerConfig: {
    asar: true,
    // Application identifiers and icons for production builds
    // appId is used on Windows/Linux; appBundleId is used on macOS
    appId: 'com.agentzero.desktop',
    appBundleId: 'com.agentzero.desktop', // macOS bundle identifier
    // Base icon path without extension; provide the following files before distribution:
    //  - assets/icon.icns (macOS)
    //  - assets/icon.ico (Windows)
    //  - assets/icon.png (Linux)
    icon: './assets/icon',

    // Windows-specific metadata
    // ProductName should align with package.json productName
    win32metadata: {
      ProductName: 'desktop',
      // Map to appId so notifications and taskbar grouping work correctly
      AppUserModelID: 'com.agentzero.desktop',
    },

    // macOS signing & notarization placeholders (fill when distributing)
    // Signing is required for Gatekeeper; notarization is required for distribution outside the App Store
    osxSign: {
      // Replace with your Developer ID Application identity, e.g. "Developer ID Application: Your Name (TEAMID)"
      identity: '',
      hardenedRuntime: true,
      // Optionally set entitlements if needed
      // entitlements: './entitlements.plist',
      // 'entitlements-inherit': './entitlements.plist',
      // signature-flags: 'library',
    },
    osxNotarize: {
      // Replace with Apple ID/email used for notarization
      appleId: '',
      // App-specific password or keychain profile reference (e.g., "@keychain:AC_PASSWORD")
      appleIdPassword: '',
      // Your Apple Team ID
      teamId: '',
    },
  },
  rebuildConfig: {},
  makers: [new MakerSquirrel({}), new MakerZIP({}, ['darwin']), new MakerRpm({}), new MakerDeb({})],
  plugins: [
    ...(isStart ? [] : [new AutoUnpackNativesPlugin({})]),
    new WebpackPlugin({
      mainConfig,
      renderer: {
        config: rendererConfig,
        entryPoints: [
          {
            html: './src/index.html',
            js: './src/renderer.ts',
            name: 'main_window',
            preload: {
              js: './src/preload.ts',
            },
          },
        ],
      },
    }),
    ...(isStart
      ? []
      : [
          // Fuses are used to enable/disable various Electron functionality
          // at package time, before code signing the application
          new FusesPlugin({
            version: FuseVersion.V1,
            [FuseV1Options.RunAsNode]: false,
            [FuseV1Options.EnableCookieEncryption]: true,
            [FuseV1Options.EnableNodeOptionsEnvironmentVariable]: false,
            [FuseV1Options.EnableNodeCliInspectArguments]: false,
            [FuseV1Options.EnableEmbeddedAsarIntegrityValidation]: true,
            [FuseV1Options.OnlyLoadAppFromAsar]: true,
          }),
        ]),
  ],
};

export default config;
