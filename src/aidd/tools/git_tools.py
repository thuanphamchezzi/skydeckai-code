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
                    "WHEN TO USE: When you need to set up version control for a project, "
                    "start tracking files with Git, or begin a new Git-based workflow. "
                    "Useful for new projects or for adding version control to existing code. "
                    "WHEN NOT TO USE: When a Git repository already exists in the target location. "
                    "RETURNS: A confirmation message indicating that the Git repository was initialized "
                    "successfully, including the path and initial branch name. If the specified directory "
                    "doesn't exist, it will be created automatically. Directory must be within the allowed workspace.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path where to initialize the repository. This will be the root directory of the Git "
                                   "repository. Examples: '.', 'my-project', 'src/module'. Both absolute and relative "
                                   "paths are supported, but must be within the allowed workspace."
                },
                "initial_branch": {
                    "type": "string",
                    "description": "Name of the initial branch to create. Common values are 'main' (modern default) or "
                                   "'master' (legacy default). Examples: 'main', 'develop', 'trunk'. If not specified, "
                                   "'main' will be used.",
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
                    "WHEN TO USE: When you need to check what files have been modified, added, or deleted in a repository, "
                    "understand the current state of the working directory, or determine which files are staged for commit. "
                    "Useful before committing changes, when troubleshooting repository state, or for confirming which "
                    "files have been modified. "
                    "WHEN NOT TO USE: When you need to see the actual content changes (use git_diff_unstaged or git_diff_staged instead), "
                    "when you need to view commit history (use git_log instead), or when you need information about a specific "
                    "commit (use git_show instead). "
                    "RETURNS: Text output showing the current branch, tracking information, and status of all files in the "
                    "repository, including staged, unstaged, and untracked files. Repository must be within the allowed directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Path to git repository. This must be a directory containing a valid Git repository. "
                                   "Examples: '.', 'my-project', '/absolute/path/to/repo'. Both absolute and relative paths "
                                   "are supported, but must be within the allowed workspace."
                }
            },
            "required": ["repo_path"]
        }
    }

def git_diff_unstaged_tool():
    return {
        "name": "git_diff_unstaged",
        "description": "Shows changes in working directory not yet staged for commit. "
                    "WHEN TO USE: When you need to see the exact content changes that have been made to files but not yet "
                    "added to the staging area. Useful for reviewing modifications before staging them, understanding what "
                    "changes have been made since the last commit, or inspecting file differences in detail. "
                    "WHEN NOT TO USE: When you only need to know which files have been modified without seeing the changes "
                    "(use git_status instead), when you want to see changes that are already staged (use git_diff_staged instead), "
                    "or when you want to compare with a specific branch (use git_diff instead). "
                    "RETURNS: A unified diff output showing the exact changes made to files that have not yet been staged, "
                    "including added, deleted, and modified lines with proper context. If no unstaged changes exist, it will "
                    "indicate that. Repository must be within the allowed directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Path to git repository. This must be a directory containing a valid Git repository. "
                                   "Examples: '.', 'my-project', '/absolute/path/to/repo'. Both absolute and relative paths "
                                   "are supported, but must be within the allowed workspace."
                }
            },
            "required": ["repo_path"]
        }
    }

def git_diff_staged_tool():
    return {
        "name": "git_diff_staged",
        "description": "Shows changes staged for commit. "
                    "WHEN TO USE: When you need to see the exact content changes that have been added to the staging area "
                    "and are ready to be committed. Useful for reviewing modifications before committing them, verifying "
                    "that the right changes are staged, or inspecting file differences in detail. "
                    "WHEN NOT TO USE: When you only need to know which files are staged without seeing the changes "
                    "(use git_status instead), when you want to see changes that are not yet staged (use git_diff_unstaged instead), "
                    "or when you want to compare with a specific branch (use git_diff instead). "
                    "RETURNS: A unified diff output showing the exact changes that have been staged, including added, "
                    "deleted, and modified lines with proper context. If no staged changes exist, it will indicate that. "
                    "Repository must be within the allowed directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Path to git repository. This must be a directory containing a valid Git repository. "
                                   "Examples: '.', 'my-project', '/absolute/path/to/repo'. Both absolute and relative paths "
                                   "are supported, but must be within the allowed workspace."
                }
            },
            "required": ["repo_path"]
        }
    }

def git_diff_tool():
    return {
        "name": "git_diff",
        "description": "Shows differences between branches or commits. "
                    "WHEN TO USE: When you need to compare the current branch with another branch or commit, "
                    "see what changes were made in a specific branch, or analyze differences between different "
                    "versions of the code. Useful for code reviews, understanding changes between versions, or "
                    "preparing for merges. "
                    "WHEN NOT TO USE: When you want to see only unstaged changes (use git_diff_unstaged instead), "
                    "when you want to see only staged changes (use git_diff_staged instead), or when you just need "
                    "a list of changed files without content details (use git_status instead). "
                    "RETURNS: A unified diff output showing the exact differences between the current branch and "
                    "the specified target branch or commit, including added, deleted, and modified lines with proper "
                    "context. If no differences exist, it will indicate that. Repository must be within the allowed directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Path to git repository. This must be a directory containing a valid Git repository. "
                                   "Examples: '.', 'my-project', '/absolute/path/to/repo'. Both absolute and relative paths "
                                   "are supported, but must be within the allowed workspace."
                },
                "target": {
                    "type": "string",
                    "description": "Target branch or commit to compare with the current branch. This can be a branch name, "
                                   "commit hash, or reference like HEAD~1. Examples: 'main', 'develop', 'feature/new-feature', "
                                   "'a1b2c3d' (commit hash)."
                }
            },
            "required": ["repo_path", "target"]
        }
    }

def git_commit_tool():
    return {
        "name": "git_commit",
        "description": "Records changes to the repository by creating a new commit. "
                    "WHEN TO USE: When you have staged changes that you want to permanently record in the repository history, "
                    "after using git_add to stage your changes, or when you've completed a logical unit of work that should "
                    "be captured. Useful after reviewing staged changes with git_diff_staged and confirming they're ready to commit. "
                    "WHEN NOT TO USE: When you haven't staged any changes yet (use git_add first), when you want to see what "
                    "changes would be committed (use git_diff_staged instead), or when you want to undo staged changes "
                    "(use git_reset instead). "
                    "RETURNS: A confirmation message with the commit hash if successful, or a message indicating that there "
                    "are no changes staged for commit. For new repositories without commits, checks if there are staged files. "
                    "Repository must be within the allowed directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Path to git repository. This must be a directory containing a valid Git repository. "
                                   "Examples: '.', 'my-project', '/absolute/path/to/repo'. Both absolute and relative paths "
                                   "are supported, but must be within the allowed workspace."
                },
                "message": {
                    "type": "string",
                    "description": "Commit message that describes the changes being committed. This message will be permanently "
                                   "recorded in the repository history and should clearly describe what changes were made and why. "
                                   "Examples: 'Fix bug in login function', 'Add pagination to user list', 'Update documentation for API endpoints'."
                }
            },
            "required": ["repo_path", "message"]
        }
    }

def git_add_tool():
    return {
        "name": "git_add",
        "description": "Adds file contents to the staging area. "
                    "WHEN TO USE: When you want to prepare modified files for commit, select specific files to include "
                    "in the next commit, or track new files in the repository. This is typically the first step in the "
                    "commit workflow after making changes. "
                    "WHEN NOT TO USE: When you want to undo staging (use git_reset instead), or when there are no changes to stage. "
                    "RETURNS: A confirmation message listing the files that were successfully staged for commit. "
                    "Repository must be within the allowed directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Path to git repository. This must be a directory containing a valid Git repository. "
                                   "Examples: '.', 'my-project', '/absolute/path/to/repo'. Both absolute and relative paths "
                                   "are supported, but must be within the allowed workspace."
                },
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of file paths to stage for the next commit. These paths should be relative to the "
                                   "repository root. Can include specific files, directories, or patterns. "
                                   "Examples: ['README.md'], ['src/main.py', 'docs/index.html'], ['*.js'] to stage all "
                                   "JavaScript files in the current directory."
                }
            },
            "required": ["repo_path", "files"]
        }
    }

def git_reset_tool():
    return {
        "name": "git_reset",
        "description": "Unstages all staged changes. "
                    "WHEN TO USE: When you want to undo staging operations, remove files from the staging area without "
                    "losing changes, or start over with your staging selections. Useful when you accidentally staged files "
                    "that shouldn't be committed or need to reorganize what will be included in the next commit. "
                    "WHEN NOT TO USE: When you want to keep some staged changes (this tool unstages everything), when you "
                    "want to discard changes completely (not just unstage them), or when you need to modify commit history. "
                    "RETURNS: A confirmation message indicating that all changes have been successfully unstaged. For new "
                    "repositories without commits, it removes all files from the index. "
                    "Repository must be within the allowed directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Path to git repository. This must be a directory containing a valid Git repository. "
                                   "Examples: '.', 'my-project', '/absolute/path/to/repo'. Both absolute and relative paths "
                                   "are supported, but must be within the allowed workspace."
                }
            },
            "required": ["repo_path"]
        }
    }

def git_log_tool():
    return {
        "name": "git_log",
        "description": "Shows the commit logs. "
                    "WHEN TO USE: When you need to view the commit history of a repository, check who made specific changes, "
                    "understand the evolution of a project over time, or find a specific commit by its description. Useful "
                    "for investigating the project history, finding when features were added, or understanding code changes. "
                    "WHEN NOT TO USE: When you need to see the actual changes in a commit (use git_show instead), when you "
                    "need to compare branches (use git_diff instead), or when you just want to know the current repository "
                    "status (use git_status instead). "
                    "RETURNS: Text output listing commit history with details for each commit including hash, author, date, "
                    "and commit message. For new repositories, indicates that no commits exist yet. "
                    "Repository must be within the allowed directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Path to git repository. This must be a directory containing a valid Git repository. "
                                   "Examples: '.', 'my-project', '/absolute/path/to/repo'. Both absolute and relative paths "
                                   "are supported, but must be within the allowed workspace."
                },
                "max_count": {
                    "type": "integer",
                    "description": "Maximum number of commits to show in the history. This limits the output to the most "
                                   "recent N commits. Examples: 5 to show the last five commits, 20 to show more history. "
                                   "Higher values may result in longer output. If not specified, defaults to 10.",
                    "default": 10
                }
            },
            "required": ["repo_path"]
        }
    }

def git_create_branch_tool():
    return {
        "name": "git_create_branch",
        "description": "Creates a new branch in a git repository. "
                    "WHEN TO USE: When you need to start working on a new feature, create an isolated environment for "
                    "development, branch off from the main codebase, or prepare for a pull request. Useful for implementing "
                    "features without affecting the main codebase, fixing bugs in isolation, or managing parallel development "
                    "workflows. "
                    "WHEN NOT TO USE: When the repository has no commits yet (make an initial commit first), when you just "
                    "want to switch to an existing branch (use git_checkout instead), or when you want to see differences "
                    "between branches (use git_diff instead). "
                    "RETURNS: A confirmation message indicating that the branch was successfully created and which branch "
                    "it was created from. Requires that the repository has at least one commit. "
                    "Repository must be within the allowed directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Path to git repository. This must be a directory containing a valid Git repository. "
                                   "Examples: '.', 'my-project', '/absolute/path/to/repo'. Both absolute and relative paths "
                                   "are supported, but must be within the allowed workspace."
                },
                "branch_name": {
                    "type": "string",
                    "description": "Name of the new branch to create. Should follow git branch naming conventions. "
                                   "Examples: 'feature/user-auth', 'bugfix/login-issue', 'release/1.0.0'."
                },
                "base_branch": {
                    "type": "string",
                    "description": "Starting point for the new branch. This can be a branch name, tag, or commit hash from "
                                   "which the new branch will be created. If not specified, the current active branch is "
                                   "used as the base. Examples: 'main', 'develop', 'v1.0' (tag), 'a1b2c3d' (commit hash).",
                    "default": None
                }
            },
            "required": ["repo_path", "branch_name"]
        }
    }

def git_checkout_tool():
    return {
        "name": "git_checkout",
        "description": "Switches branches in a git repository. "
                    "WHEN TO USE: When you need to switch your working directory to a different branch, view or work on "
                    "code from another branch, or prepare for merging branches. Useful for moving between feature branches, "
                    "switching to the main branch to pull updates, or starting work on a different task. "
                    "WHEN NOT TO USE: When the repository has no commits yet (make an initial commit first), when you want "
                    "to create a new branch (use git_create_branch instead), or when you have uncommitted changes that would "
                    "be overwritten. "
                    "RETURNS: A confirmation message indicating that the branch was successfully checked out. Requires that "
                    "the repository has at least one commit and that the specified branch exists. "
                    "Repository must be within the allowed directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Path to git repository. This must be a directory containing a valid Git repository. "
                                   "Examples: '.', 'my-project', '/absolute/path/to/repo'. Both absolute and relative paths "
                                   "are supported, but must be within the allowed workspace."
                },
                "branch_name": {
                    "type": "string",
                    "description": "Name of branch to checkout. This must be an existing branch in the repository. "
                                   "Examples: 'main', 'develop', 'feature/user-authentication'. The branch must exist "
                                   "in the repository or the command will fail."
                }
            },
            "required": ["repo_path", "branch_name"]
        }
    }

def git_show_tool():
    return {
        "name": "git_show",
        "description": "Shows the contents of a specific commit. "
                    "WHEN TO USE: When you need to examine the exact changes introduced by a particular commit, understand "
                    "what was modified in a specific revision, or analyze the details of historical changes. Useful for code "
                    "reviews, understanding the implementation of a feature, or troubleshooting when a bug was introduced. "
                    "WHEN NOT TO USE: When the repository has no commits yet, when you only need a list of commits without "
                    "details (use git_log instead), or when you want to compare branches or arbitrary revisions (use "
                    "git_diff instead). "
                    "RETURNS: Detailed information about the specified commit including commit hash, author, date, commit message, "
                    "and a unified diff showing all changes introduced by that commit. For the first commit in a repository, "
                    "shows the complete file contents. Repository must be within the allowed directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Path to git repository. This must be a directory containing a valid Git repository. "
                                   "Examples: '.', 'my-project', '/absolute/path/to/repo'. Both absolute and relative paths "
                                   "are supported, but must be within the allowed workspace."
                },
                "revision": {
                    "type": "string",
                    "description": "The revision to show details for. This can be a commit hash (full or abbreviated), branch name, "
                                   "tag, or reference like HEAD~1. Examples: 'a1b2c3d' (commit hash), 'main' (branch), 'v1.0' (tag), "
                                   "'HEAD~3' (third commit before current HEAD)."
                }
            },
            "required": ["repo_path", "revision"]
        }
    }

def git_clone_tool():
    return {
        "name": "git_clone",
        "description": "Clones a remote Git repository into a new directory. "
                    "WHEN TO USE: When you need to download a copy of an existing Git repository, start working with a "
                    "remote codebase, or initialize a new local copy of a project. Useful for contributing to open-source "
                    "projects, setting up new development environments, or accessing shared code repositories. "
                    "WHEN NOT TO USE: When the target directory already contains a Git repository, when you only need to "
                    "update an existing repository (use git_pull instead), or when you want to create a new empty repository "
                    "(use git_init instead). "
                    "RETURNS: A confirmation message indicating that the repository was successfully cloned, including "
                    "the source URL and destination directory. Repository must be cloned to a location within the allowed directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL of the remote repository to clone. This can be an HTTPS URL, SSH URL, or local path. "
                                   "Examples: 'https://github.com/username/repo.git', 'git@github.com:username/repo.git', "
                                   "'/path/to/local/repo'. Security restrictions may apply to certain URLs."
                },
                "target_path": {
                    "type": "string",
                    "description": "Directory where the repository will be cloned. If the directory doesn't exist, it will "
                                   "be created. If it exists, it must be empty. Examples: 'my-project', 'src/external', "
                                   "'path/to/clone'. Both absolute and relative paths are supported, but must be within "
                                   "the allowed workspace."
                },
                "branch": {
                    "type": "string",
                    "description": "Branch to check out after cloning. If not specified, the repository's default branch "
                                   "is used. Examples: 'main', 'develop', 'feature/new-feature'. Specifying a branch can "
                                   "save time when working with large repositories.",
                    "default": None
                }
            },
            "required": ["url", "target_path"]
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

async def handle_git_clone(arguments: dict) -> List[TextContent]:
    """Handle cloning a remote git repository."""
    url = arguments.get("url")
    if not url:
        raise ValueError("url is required")
    target_path = arguments.get("target_path")
    if not target_path:
        raise ValueError("target_path is required")
    branch = arguments.get("branch")

    # Determine full path based on whether input is absolute or relative
    if os.path.isabs(target_path):
        full_path = os.path.abspath(target_path)
    else:
        full_path = os.path.abspath(os.path.join(state.allowed_directory, target_path))

    # Security check
    if not full_path.startswith(state.allowed_directory):
        raise ValueError(f"Access denied: Path ({full_path}) must be within allowed directory")

    try:
        # Check if directory exists and is empty
        if os.path.exists(full_path):
            if os.path.isdir(full_path) and os.listdir(full_path):
                raise ValueError(f"Target directory '{full_path}' is not empty")
            elif not os.path.isdir(full_path):
                raise ValueError(f"Target path '{full_path}' exists but is not a directory")
        else:
            # Create directory if it doesn't exist
            os.makedirs(full_path, exist_ok=True)

        # Clone options
        clone_args = {}
        if branch:
            clone_args["branch"] = branch

        # Perform the clone
        repo = git.Repo.clone_from(url, full_path, **clone_args)

        branch_info = f" (branch: {branch})" if branch else ""
        return [TextContent(
            type="text",
            text=f"Repository successfully cloned from {url} to {target_path}{branch_info}"
        )]
    except Exception as e:
        raise ValueError(f"Error cloning repository: {str(e)}")
