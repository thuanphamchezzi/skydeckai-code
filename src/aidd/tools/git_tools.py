import os
from typing import List

import git
from mcp.types import TextContent

from .state import state


def _get_repo(repo_path: str) -> git.Repo:
    """Helper function to get git repo with validation."""
    # Determine full path based on whether input is absolute or relative
    if os.path.isabs(repo_path):
        full_path = os.path.abspath(repo_path)
    else:
        full_path = os.path.abspath(os.path.join(state.allowed_directory, repo_path))

    # Security check
    if not full_path.startswith(state.allowed_directory):
        raise ValueError(f"Access denied: Path ({full_path}) must be within allowed directory")

    try:
        return git.Repo(full_path)
    except git.InvalidGitRepositoryError:
        raise ValueError(f"Not a valid git repository: {full_path}")
    except Exception as e:
        raise ValueError(f"Error accessing git repository at '{full_path}': {str(e)}")

def git_init_tool():
    return {
        "name": "git_init",
        "description": "Initialize a new Git repository. "
                    "Creates a new Git repository in the specified directory. "
                    "If the directory doesn't exist, it will be created. "
                    "Directory must be within the allowed directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path where to initialize the repository"
                },
                "initial_branch": {
                    "type": "string",
                    "description": "Name of the initial branch (defaults to 'main')",
                    "default": "main"
                }
            },
            "required": ["path"]
        }
    }

async def handle_git_init(arguments: dict) -> List[TextContent]:
    """Handle initializing a new git repository."""
    path = arguments["path"]
    initial_branch = arguments.get("initial_branch", "main")

    # Validate and create directory if needed
    full_path = os.path.abspath(os.path.join(state.allowed_directory, path))
    if not full_path.startswith(state.allowed_directory):
        raise ValueError(f"Access denied: Path ({full_path}) must be within allowed directory")

    try:
        os.makedirs(full_path, exist_ok=True)
        git.Repo.init(full_path, initial_branch=initial_branch)
        return [TextContent(
            type="text",
            text=f"Initialized empty Git repository in {path} with initial branch '{initial_branch}'"
        )]
    except Exception as e:
        raise ValueError(f"Error initializing repository at '{full_path}': {str(e)}")

def git_status_tool():
    return {
        "name": "git_status",
        "description": "Shows the working tree status of a git repository. "
                    "Returns information about staged, unstaged, and untracked files. "
                    "Repository must be within the allowed directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Path to git repository"
                }
            },
            "required": ["repo_path"]
        }
    }

def git_diff_unstaged_tool():
    return {
        "name": "git_diff_unstaged",
        "description": "Shows changes in working directory not yet staged for commit. "
                    "Returns a unified diff format of all unstaged changes. "
                    "Repository must be within the allowed directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Path to git repository"
                }
            },
            "required": ["repo_path"]
        }
    }

def git_diff_staged_tool():
    return {
        "name": "git_diff_staged",
        "description": "Shows changes staged for commit. "
                    "Returns a unified diff format of all staged changes. "
                    "Repository must be within the allowed directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Path to git repository"
                }
            },
            "required": ["repo_path"]
        }
    }

def git_diff_tool():
    return {
        "name": "git_diff",
        "description": "Shows differences between branches or commits. "
                    "Returns a unified diff format comparing current state with target. "
                    "Repository must be within the allowed directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Path to git repository"
                },
                "target": {
                    "type": "string",
                    "description": "Target branch or commit to compare with"
                }
            },
            "required": ["repo_path", "target"]
        }
    }

def git_commit_tool():
    return {
        "name": "git_commit",
        "description": "Records changes to the repository. "
                    "Commits all staged changes with the provided message. "
                    "Repository must be within the allowed directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Path to git repository"
                },
                "message": {
                    "type": "string",
                    "description": "Commit message"
                }
            },
            "required": ["repo_path", "message"]
        }
    }

def git_add_tool():
    return {
        "name": "git_add",
        "description": "Adds file contents to the staging area. "
                    "Stages specified files for the next commit. "
                    "Repository must be within the allowed directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Path to git repository"
                },
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of file paths to stage"
                }
            },
            "required": ["repo_path", "files"]
        }
    }

def git_reset_tool():
    return {
        "name": "git_reset",
        "description": "Unstages all staged changes. "
                    "Removes all files from the staging area. "
                    "Repository must be within the allowed directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Path to git repository"
                }
            },
            "required": ["repo_path"]
        }
    }

def git_log_tool():
    return {
        "name": "git_log",
        "description": "Shows the commit logs. "
                    "Returns information about recent commits including hash, author, date, and message. "
                    "Repository must be within the allowed directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Path to git repository"
                },
                "max_count": {
                    "type": "integer",
                    "description": "Maximum number of commits to show",
                    "default": 10
                }
            },
            "required": ["repo_path"]
        }
    }

def git_create_branch_tool():
    return {
        "name": "git_create_branch",
        "description": "Creates a new branch. "
                    "Creates a new branch from the specified base branch or current HEAD. "
                    "Repository must be within the allowed directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Path to git repository"
                },
                "branch_name": {
                    "type": "string",
                    "description": "Name of the new branch"
                },
                "base_branch": {
                    "type": "string",
                    "description": "Starting point for the new branch (optional)",
                    "default": None
                }
            },
            "required": ["repo_path", "branch_name"]
        }
    }

def git_checkout_tool():
    return {
        "name": "git_checkout",
        "description": "Switches branches. "
                    "Checks out the specified branch. "
                    "Repository must be within the allowed directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Path to git repository"
                },
                "branch_name": {
                    "type": "string",
                    "description": "Name of branch to checkout"
                }
            },
            "required": ["repo_path", "branch_name"]
        }
    }

def git_show_tool():
    return {
        "name": "git_show",
        "description": "Shows the contents of a commit. "
                    "Returns detailed information about a specific commit including the changes it introduced. "
                    "Repository must be within the allowed directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Path to git repository"
                },
                "revision": {
                    "type": "string",
                    "description": "The revision (commit hash, branch name, tag) to show"
                }
            },
            "required": ["repo_path", "revision"]
        }
    }

async def handle_git_status(arguments: dict) -> List[TextContent]:
    """Handle getting git repository status."""
    repo = _get_repo(arguments["repo_path"])
    try:
        status = repo.git.status()
        return [TextContent(
            type="text",
            text=f"Repository status:\n{status}"
        )]
    except Exception as e:
        raise ValueError(f"Error getting repository status at '{repo.working_dir}': {str(e)}")

async def handle_git_diff_unstaged(arguments: dict) -> List[TextContent]:
    """Handle getting unstaged changes."""
    repo = _get_repo(arguments["repo_path"])
    try:
        # For new repos without commits, show diff of staged files
        if not repo.head.is_valid():
            # Get the diff against an empty tree
            diff = repo.git.diff("--no-index", "/dev/null", repo.working_dir)
        else:
            diff = repo.git.diff()

        if not diff:
            return [TextContent(
                type="text",
                text="No unstaged changes found."
            )]
        return [TextContent(
            type="text",
            text=f"Unstaged changes:\n{diff}"
        )]
    except Exception as e:
        raise ValueError(f"Error getting unstaged changes: {str(e)}")

async def handle_git_diff_staged(arguments: dict) -> List[TextContent]:
    """Handle getting staged changes."""
    repo = _get_repo(arguments["repo_path"])
    try:
        # For new repos without commits, show all staged files
        if not repo.head.is_valid():
            if repo.index.entries:
                diff = repo.git.diff("--cached", "--no-index", "/dev/null", "--")
            else:
                diff = ""
        else:
            diff = repo.git.diff("--cached")
        if not diff:
            return [TextContent(
                type="text",
                text="No staged changes found."
            )]
        return [TextContent(
            type="text",
            text=f"Staged changes:\n{diff}"
        )]
    except Exception as e:
        raise ValueError(f"Error getting staged changes at '{repo.working_dir}': {str(e)}")

async def handle_git_diff(arguments: dict) -> List[TextContent]:
    """Handle getting diff between branches or commits."""
    repo = _get_repo(arguments["repo_path"])
    target = arguments["target"]
    try:
        # Check if repository has any commits
        if not repo.head.is_valid():
            raise ValueError(f"Cannot diff against '{target}' in repository at '{repo.working_dir}': No commits exist yet")
        else:
            diff = repo.git.diff(target)
        if not diff:
            return [TextContent(
                type="text",
                text=f"No differences found with {target}."
            )]
        return [TextContent(
            type="text",
            text=f"Diff with {target}:\n{diff}"
        )]
    except Exception as e:
        raise ValueError(f"Error getting diff at '{repo.working_dir}': {str(e)}")

async def handle_git_commit(arguments: dict) -> List[TextContent]:
    """Handle committing changes."""
    repo = _get_repo(arguments["repo_path"])
    message = arguments["message"]
    try:
        # Check if this is the first commit
        is_initial_commit = not repo.head.is_valid()

        if not is_initial_commit:
            # For non-initial commits, check if there are staged changes
            if not repo.index.diff("HEAD"):
                return [TextContent(
                    type="text",
                    text="No changes staged for commit."
                )]
        elif not repo.index.entries:
            return [TextContent(type="text", text="No files staged for initial commit.")]

        # Perform the commit
        commit = repo.index.commit(message)
        return [TextContent(
            type="text",
            text=f"Changes committed successfully with hash {commit.hexsha}"
        )]
    except Exception as e:
        raise ValueError(f"Error committing changes at '{repo.working_dir}': {str(e)}")

async def handle_git_add(arguments: dict) -> List[TextContent]:
    """Handle staging files."""
    repo = _get_repo(arguments["repo_path"])
    files = arguments["files"]
    try:
        repo.index.add(files)
        return [TextContent(
            type="text",
            text=f"Successfully staged the following files:\n{', '.join(files)}"
        )]
    except Exception as e:
        raise ValueError(f"Error staging files at '{repo.working_dir}': {str(e)}")

async def handle_git_reset(arguments: dict) -> List[TextContent]:
    """Handle unstaging all changes."""
    repo = _get_repo(arguments["repo_path"])
    try:
        # Check if this is a new repository without any commits
        if not repo.head.is_valid():
            # For new repos, just remove all from index
            repo.index.remove(repo.index.entries.keys())
            repo.index.write()
            return [TextContent(
                type="text",
                text="Successfully unstaged all changes (new repository)"
            )]
        else:
            repo.index.reset()  # Normal reset for repositories with commits
        return [TextContent(
            type="text",
            text="Successfully unstaged all changes"
        )]
    except Exception as e:
        raise ValueError(f"Error unstaging changes at '{repo.working_dir}': {str(e)}")

async def handle_git_log(arguments: dict) -> List[TextContent]:
    """Handle showing commit logs."""
    repo = _get_repo(arguments["repo_path"])
    max_count = arguments.get("max_count", 10)
    try:
        # Check if repository has any commits
        if not repo.head.is_valid():
            return [TextContent(
                type="text",
                text="No commits yet - this is a new repository."
            )]
        commits = list(repo.iter_commits(max_count=max_count))
        if not commits:
            return [TextContent(
                type="text",
                text="No commits found in repository."
            )]

        log_entries = []
        for commit in commits:
            log_entries.append(
                f"Commit: {commit.hexsha}\n"
                f"Author: {commit.author}\n"
                f"Date: {commit.authored_datetime}\n"
                f"Message: {commit.message}\n"
            )

        return [TextContent(
            type="text",
            text="Commit history:\n" + "\n".join(log_entries)
        )]
    except Exception as e:
        raise ValueError(f"Error getting commit logs at '{repo.working_dir}': {str(e)}")

async def handle_git_create_branch(arguments: dict) -> List[TextContent]:
    """Handle creating a new branch."""
    repo = _get_repo(arguments["repo_path"])
    branch_name = arguments["branch_name"]
    base_branch = arguments.get("base_branch")

    # Check if repository has any commits
    if not repo.head.is_valid():
        return [TextContent(
            type="text",
            text=f"Cannot create branch '{branch_name}' - no commits exist yet. Make an initial commit first."
        )]

    try:
        if base_branch:
            base = repo.refs[base_branch]
        else:  # We already checked head.is_valid() above
            base = repo.active_branch

        repo.create_head(branch_name, base)
        return [TextContent(
            type="text",
            text=f"Created branch '{branch_name}' from '{base.name}'"
        )]
    except Exception as e:
        raise ValueError(f"Error creating branch at '{repo.working_dir}': {str(e)}")

async def handle_git_checkout(arguments: dict) -> List[TextContent]:
    """Handle switching branches."""
    repo = _get_repo(arguments["repo_path"])
    branch_name = arguments["branch_name"]
    try:
        # Check if repository has any commits
        if not repo.head.is_valid():
            return [TextContent(
                type="text",
                text=f"Cannot checkout branch '{branch_name}' - no commits exist yet. Make an initial commit first."
            )]

        repo.git.checkout(branch_name)
        return [TextContent(
            type="text",
            text=f"Successfully switched to branch '{branch_name}'"
        )]
    except Exception as e:
        raise ValueError(f"Error switching branches at '{repo.working_dir}': {str(e)}")

async def handle_git_show(arguments: dict) -> List[TextContent]:
    """Handle showing commit contents."""
    repo = _get_repo(arguments["repo_path"])
    revision = arguments["revision"]
    try:
        # Check if repository has any commits
        if not repo.head.is_valid():
            return [TextContent(
                type="text",
                text=f"Cannot show revision '{revision}' - no commits exist yet."
            )]

        commit = repo.commit(revision)
        output = [
            f"Commit: {commit.hexsha}\n"
            f"Author: {commit.author}\n"
            f"Date: {commit.authored_datetime}\n"
            f"Message: {commit.message}\n"
        ]

        # Get the diff
        if commit.parents:
            parent = commit.parents[0]
            diff = parent.diff(commit, create_patch=True)
        else:
            diff = commit.diff(git.NULL_TREE, create_patch=True)

        for d in diff:
            output.append(f"\n--- {d.a_path}\n+++ {d.b_path}\n")
            output.append(d.diff.decode('utf-8'))

        return [TextContent(
            type="text",
            text="".join(output)
        )]
    except Exception as e:
        raise ValueError(f"Error showing commit at '{repo.working_dir}': {str(e)}")
