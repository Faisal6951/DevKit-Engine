# 🛠️ DevKit Engine (Apex)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

A minimalist, high-performance Windows environment provisioning and setup deployment engine. Built for engineers who need to turn a fresh Windows installation into a fully configured development workstation in a single click.

---

## 🎯 Key Capabilities

*   ⚡ **Automated WinGet Provisioning:** Silently installs critical development tools (Git, VS Code, Cursor, Docker Desktop, Google Chrome, and more) using native Windows package management hooks.
*   🔒 **Isolated Local Vault:** Securely manages system environment profiles and local setup credentials entirely offline via a localized configuration mapping system.
*   ⚙️ **Dynamic Branding Control:** Built on top of a central command configuration pattern. Rebrand, rename, or swap system interface icon assets instantly by modifying a single file.
*   🚀 **Zero Footprint Portable Exe:** Packaged via automated integration pipelines into a lightweight, standalone binary (`.exe`) that runs directly from a portable USB drive or local directory.

---

## 🛠️ Integrated Toolchains

The installation engine comes pre-configured to silently bundle and provision the following software suites out of the box:

| Software | WinGet Package ID | Purpose |
| :--- | :--- | :--- |
| **Google Chrome** | `Google.Chrome` | Primary Target Web Browser |
| **Git Bash** | `Git.Git` | Native Distributed Version Control |
| **Visual Studio Code** | `Microsoft.VisualStudioCode` | Extensible Code & Text Editor |
| **Cursor** | `Anysphere.Cursor` | AI-First Integrated Development Environment |
| **Docker Desktop** | `Docker.DockerDesktop` | Containerization & Virtualization |
| **VLC Media Player** | `VideoLAN.VLC` | High-Efficiency Open-Source Media Processing |

---

## 🚀 Getting Started

### Prerequisites
*   **Operating System:** Windows 10 or Windows 11
*   **Permissions:** Administrative privileges (required for silent application installation routines)

### Installation
1. Head over to the [GitHub Releases](https://github.com/Faisal6951/DevKit-Engine/releases) page.
2. Download the latest compiled release architecture (`Apex.exe`).
3. Run the application as an **Administrator** to allow the `winget` silent execution process to interact with your system packages.

---

## 💻 Technical Architecture & Tech Stack

This project is decoupled using a clean Model-View-Controller (MVC) architectural separation to keep UI code separate from core deployment execution logic:

*   **Language Infrastructure:** Python 3.12
*   **Graphical User Interface:** `CustomTkinter` (Modernized dark/light adaptive variant of traditional Tkinter)
*   **Automation Driver:** Native Windows `subprocess` execution pipes hooking into the `winget` CLI core.
*   **Continuous Integration / Deployment:** Managed via automated GitHub Actions cloud virtual machines.

---

## 📝 License & Security

Distributed under the **MIT License**. See `LICENSE` for more information.

*DevKit Engine operates entirely locally. It does not track, collect, scrape, or transmit system states, telemetry data, or configuration credentials to external cloud endpoints.*
