- [x] Verify that the copilot-instructions.md file in the .github directory is created. Created the file with project checklist.
- [x] Clarify Project Requirements. Requirements provided for Flask food donation app.
- [x] Scaffold the Project. Created all necessary files and directories for the Flask app.
- [x] Customize the Project. Implemented all features: authentication, dashboards, food posting, booking, payment mock.
- [x] Install Required Extensions. No extensions needed for this project.
- [x] Compile the Project. Installed dependencies and ran the app successfully.
- [x] Create and Run Task. No tasks.json needed; app runs with python app.py.
- [x] Launch the Project. App is ready to run with python app.py.
- [x] Ensure Documentation is Complete. README.md created with setup instructions.
- Work through each checklist item systematically.
- Keep communication concise and focused.
- Follow development best practices.
- Use '.' as the working directory unless user specifies otherwise.
- Avoid adding media or external links unless explicitly requested.
- Use placeholders only with a note that they should be replaced.
- Use VS Code API tool only for VS Code extension projects.
- Once the project is created, it is already opened in Visual Studio Code—do not suggest commands to open this project in vscode.
- If the project setup information has additional rules, follow them strictly.

FOLDER CREATION RULES:
- Always use the current directory as the project root.
- If you are running any terminal commands, use the '.' argument to ensure that the current working directory is used ALWAYS.
- Do not create a new folder unless the user explicitly requests it besides a .vscode folder for a tasks.json file.
- If any of the scaffolding commands mention that the folder name is not correct, let the user know to create a new folder with the correct name and then reopen it again in vscode.

EXTENSION INSTALLATION RULES:
- Only install extension specified by the get_project_setup_info tool. DO NOT INSTALL any other extensions.

PROJECT CONTENT RULES:
- If the user has not specified project details, assume they want a "Hello World" project as a starting point.
- Avoid adding links of any type (URLs, files, folders, etc.) or integrations that are not explicitly required.
- Avoid generating images, videos, or any other media files unless explicitly requested.
- If a feature is assumed but not confirmed, prompt the user for clarification before including it.
- If you are working on a VS Code extension, use the VS Code API tool with a query to find relevant VS Code API references and samples.

TASK COMPLETION RULES:
- Your task is complete when:
  - Project is successfully scaffolded and compiled without errors
  - copilot-instructions.md file in the .github directory exists and contains current project information
  - README.md file exists and is up to date
  - User is provided with clear instructions to debug/launch the project