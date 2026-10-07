# Privacy

DevKit Engine runs entirely on your Windows machine.

- It does not create an online account for you.
- It does not send telemetry, usage analytics, or crash reports.
- It does not upload credentials, tokens, or package selections.
- WinGet talks only to Microsoft’s package sources and the publishers you selected.
- Optional Git / Docker / Google values stay in `devkit_vault.json` next to the app. Token and password fields are encrypted with Windows DPAPI, bound to your Windows user.
- The clipboard helper runs only while a deployment is active, and only to open login URLs in a local Chrome profile. It does not transmit clipboard contents.

Uninstall is deletion of the executable and, if you want, `devkit_vault.json` and the optional `DevKit/profiles` folder.
