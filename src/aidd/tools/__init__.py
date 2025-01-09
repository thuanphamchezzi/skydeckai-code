from .path_tools import (
    get_allowed_directory_tool, update_allowed_directory_tool,
    handle_get_allowed_directory, handle_update_allowed_directory
)
from .directory_tools import (
    list_directory_tool, handle_list_directory,
    create_directory_tool, handle_create_directory,
    directory_tree_tool, handle_directory_tree
)
from .file_tools import (
    read_file_tool, read_multiple_files_tool, write_file_tool,
    handle_read_file, handle_read_multiple_files, handle_write_file, edit_file_tool, handle_edit_file,
    move_file_tool, handle_move_file,
    search_files_tool, handle_search_files,
    delete_file_tool, handle_delete_file,
    get_file_info_tool, handle_get_file_info,
)
from .code_execution import (
    execute_code_tool, handle_execute_code
)
from .code_analysis import (
    tree_sitter_map_tool, handle_tree_sitter_map
)
from .git_tools import (
    git_init_tool, git_status_tool, git_diff_unstaged_tool, git_diff_staged_tool, git_diff_tool, git_commit_tool,
    git_add_tool, git_reset_tool, git_log_tool, git_create_branch_tool, git_checkout_tool, git_show_tool,
    handle_git_init, handle_git_status, handle_git_diff_unstaged, handle_git_diff_staged, handle_git_diff, handle_git_commit,
    handle_git_add, handle_git_reset, handle_git_log, handle_git_create_branch, handle_git_checkout, handle_git_show
)
from .system_tools import (
    get_system_info_tool, handle_get_system_info
)

# Export all tools definitions
TOOL_DEFINITIONS = [
    get_allowed_directory_tool(),
    write_file_tool(),
    update_allowed_directory_tool(),
    create_directory_tool(),
    edit_file_tool(),
    list_directory_tool(),
    read_file_tool(),
    read_multiple_files_tool(),
    move_file_tool(),
    search_files_tool(),
    delete_file_tool(),
    get_file_info_tool(),
    directory_tree_tool(),
    execute_code_tool(),
    tree_sitter_map_tool(),
    # Git tools
    git_init_tool(),
    git_status_tool(),
    git_diff_unstaged_tool(),
    git_diff_staged_tool(),
    git_diff_tool(),
    git_commit_tool(),
    git_add_tool(),
    git_reset_tool(),
    git_log_tool(),
    git_create_branch_tool(),
    git_checkout_tool(),
    git_show_tool(),
    get_system_info_tool(),
]

# Export all handlers
TOOL_HANDLERS = {
    "get_allowed_directory": handle_get_allowed_directory,
    "update_allowed_directory": handle_update_allowed_directory,
    "list_directory": handle_list_directory,
    "create_directory": handle_create_directory,
    "read_file": handle_read_file,
    "write_file": handle_write_file,
    "edit_file": handle_edit_file,
    "read_multiple_files": handle_read_multiple_files,
    "move_file": handle_move_file,
    "search_files": handle_search_files,
    "delete_file": handle_delete_file,
    "get_file_info": handle_get_file_info,
    "directory_tree": handle_directory_tree,
    "execute_code": handle_execute_code,
    "tree_sitter_map": handle_tree_sitter_map,
    # Git handlers
    "git_init": handle_git_init,
    "git_status": handle_git_status,
    "git_diff_unstaged": handle_git_diff_unstaged,
    "git_diff_staged": handle_git_diff_staged,
    "git_diff": handle_git_diff,
    "git_commit": handle_git_commit,
    "git_add": handle_git_add,
    "git_reset": handle_git_reset,
    "git_log": handle_git_log,
    "git_create_branch": handle_git_create_branch,
    "git_checkout": handle_git_checkout,
    "git_show": handle_git_show,
    "get_system_info": handle_get_system_info,
}
