# AiDD MCP Server

AiDD (AI-Driven Development) is a Model Context Protocol server designed to facilitate AI-assisted software development workflows. It provides a secure and efficient interface for AI agents to interact with local file systems and perform code analysis across multiple programming languages using tree-sitter.

## Quick Install

```bash
# Using npx
npx @michaellatman/mcp-get@latest install aidd

# Using pip
pip install aidd

# Using uv
uvx aidd
```

## Overview

AiDD implements the Model Context Protocol (MCP) to enable seamless integration between AI agents and development environments. It offers comprehensive file system operations, directory management, and advanced code analysis capabilities while maintaining strict security controls.

## Key Features

### File System Operations

-   Secure file reading, writing, and manipulation
-   Batch file operations support
-   Git-aware performance optimizations
-   Detailed file metadata access
-   Comprehensive Git operations support

### Code Analysis

-   Multi-language source code parsing
-   Structural analysis of code components
-   Function and class mapping
-   Inheritance and dependency detection

### Security

-   Strict directory access controls
-   Path traversal prevention
-   Configurable workspace boundaries
-   Safe file operation handling

## Tool Descriptions

### File Operations

#### read_file

-   path(string): Path to the file to read
-   Returns: Content of the file

#### read_multiple_files

-   paths(array of strings): List of file paths to read
-   Returns: Contents of all files with headers

#### write_file

-   path(string): Path where to write the file
-   content(string): Content to write to the file

#### edit_file

-   path(string): File to edit
-   edits(array): List of edit operations
    -   oldText(string): Text to search for
    -   newText(string): Text to replace with
-   dryRun(boolean, optional): Preview changes without applying (default: false)
-   options(object, optional):
    -   preserveIndentation(boolean): Keep existing indentation (default: true)
    -   normalizeWhitespace(boolean): Normalize spaces (default: true)
    -   partialMatch(boolean): Enable fuzzy matching (default: true)

#### move_file

-   source(string): Source path of the file or directory
-   destination(string): Destination path

#### delete_file

-   path(string): Path to the file or empty directory to delete

#### get_file_info

-   path(string): Path to the file or directory
-   Returns: Size, timestamps, and permissions

### Directory Operations

#### get_allowed_directory

Returns the current working directory that this server is allowed to access.

#### update_allowed_directory

-   directory(string): Directory to allow access to (must be absolute path)

#### list_directory

-   path(string): Path of the directory to list

#### create_directory

-   path(string): Path of the directory to create

#### directory_tree

-   path(string): Root directory to analyze

#### search_files

-   pattern(string): Pattern to search for in file names
-   path(string, optional): Starting directory for search (default: ".")
-   include_hidden(boolean, optional): Include hidden files (default: false)

### Code Analysis

#### tree_sitter_map

-   path(string): Root directory to analyze
-   Returns: Structural analysis of source code files

### Git Operations

#### git_init

-   path(string): Path where to initialize the repository
-   initial_branch(string, optional): Name of the initial branch (defaults to 'main')
-   Returns: Confirmation of repository initialization

#### git_status

-   repo_path(string): Path to git repository
-   Returns: Current status of working directory

#### git_diff_unstaged

-   repo_path(string): Path to git repository
-   Returns: Diff output of unstaged changes

#### git_diff_staged

-   repo_path(string): Path to git repository
-   Returns: Diff output of staged changes

#### git_diff

-   repo_path(string): Path to git repository
-   target(string): Target branch or commit to compare with
-   Returns: Diff output comparing current state with target

#### git_commit

-   repo_path(string): Path to git repository
-   message(string): Commit message
-   Returns: Confirmation with new commit hash

#### git_add

-   repo_path(string): Path to git repository
-   files(array of strings): List of file paths to stage
-   Returns: Confirmation of staged files

#### git_reset

-   repo_path(string): Path to git repository
-   Returns: Confirmation of unstaging operation

#### git_log

-   repo_path(string): Path to git repository
-   max_count(integer, optional): Maximum number of commits to show (default: 10)
-   Returns: Array of commit entries with hash, author, date, and message

#### git_create_branch

-   repo_path(string): Path to git repository
-   branch_name(string): Name of the new branch
-   base_branch(string, optional): Starting point for the new branch
-   Returns: Confirmation of branch creation

#### git_checkout

-   repo_path(string): Path to git repository
-   branch_name(string): Name of branch to checkout
-   Returns: Confirmation of branch switch

#### git_show

-   repo_path(string): Path to git repository
-   revision(string): The revision (commit hash, branch name, tag) to show
-   Returns: Contents of the specified commit

## Supported Languages

AiDD provides deep code analysis for multiple programming languages through tree-sitter integration:

| Language   | File Extensions                  |
| ---------- | -------------------------------- |
| Python     | .py                              |
| JavaScript | .js, .jsx, .mjs, .cjs            |
| TypeScript | .ts, .tsx                        |
| Java       | .java                            |
| C++        | .cpp, .hpp, .cc, .hh, .cxx, .hxx |
| Ruby       | .rb, .rake                       |
| Go         | .go                              |
| Rust       | .rs                              |
| PHP        | .php                             |
| C#         | .cs                              |
| Kotlin     | .kt, .kts                        |

## Configuration

AiDD stores its configuration in `~/.aidd/config.json`:

```json
{
    "allowed_directory": "/path/to/workspace"
}
```

## Claude Desktop Integration

Add this to your `claude_desktop_config.json`:

```json
"mcpServers": {
    "aidd": {
        "command": "aidd",
        "args": []
    }
}
```

## Debugging

For the best debugging experience, use the MCP Inspector:

```bash
npx @modelcontextprotocol/inspector --directory /path/to/directory/aidd/src/aidd run aidd
```

The Inspector will provide a URL to access the debugging interface in your browser.

## Security Considerations

-   All file operations are restricted to the configured allowed directory
-   Path traversal attempts are automatically blocked
-   File permissions are preserved and validated
-   Sensitive operations require explicit configuration

## Performance Optimization

-   Git-aware operations for improved performance in repositories
-   Efficient batch operations for multiple files
-   Caching of frequently accessed paths
-   Optimized code parsing for large files

## Upcoming Tools

-   GitHub tools:
    -   PR Description Generator
    -   Code Review
    -   Actions Manager
-   Pivotal Tracker tools:
    -   Story Generator
    -   Story Manager

## Development Status

Please note that AiDD is currently in development and functionality may be subject to change.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
