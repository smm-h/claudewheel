"""All DEFAULT_* configuration dicts for Y`GMo>A9@a4.Qi."""

DEFAULT_CONFIG = {
    "theme": "dark",
    "enabled_segments": [
        "profile",
        "github",
        "version",
        "directory",
        "mcp",
        "permissions",
    ],
    "default_flags": [],
    "health_check_on_launch": True,
}

DEFAULT_SEGMENTS = [
    {
        "key": "profile",
        "label": "Profile",
        "show_options": True,
        "wrap": True,
        "min_width": 8,
        "max_width": 16,
        "required": True,
        "searchable": False,
        "tab_advances": True,
        "dynamic": False,
    },
    {
        "key": "github",
        "label": "GH",
        "show_options": True,
        "wrap": True,
        "min_width": 4,
        "max_width": 12,
        "required": True,
        "searchable": False,
        "tab_advances": True,
        "dynamic": False,
    },
    {
        "key": "version",
        "label": "Ver",
        "show_options": True,
        "wrap": True,
        "min_width": 6,
        "max_width": 10,
        "required": True,
        "searchable": False,
        "tab_advances": True,
        "dynamic": True,
    },
    {
        "key": "directory",
        "label": "Dir",
        "show_options": True,
        "wrap": False,
        "min_width": 10,
        "max_width": 40,
        "required": True,
        "searchable": True,
        "tab_advances": True,
        "dynamic": True,
    },
    {
        "key": "mcp",
        "label": "MCP",
        "show_options": True,
        "wrap": True,
        "min_width": 6,
        "max_width": 12,
        "required": False,
        "searchable": False,
        "tab_advances": True,
        "dynamic": False,
    },
    {
        "key": "permissions",
        "label": "Perms",
        "show_options": True,
        "wrap": True,
        "min_width": 6,
        "max_width": 12,
        "required": False,
        "searchable": False,
        "tab_advances": True,
        "dynamic": False,
    },
]

DEFAULT_OPTIONS = {
    "profile": {
        "values": ["personal", "work", "_UC'NUN?j"],
        "metadata": {
            "personal": {"config_dir": "~/.claude-personal"},
            "work": {"config_dir": "~/.claude-work"},
            "@4Sn[TG-J": {"config_dir": "~/.claude-u(5;:35"g"},
        },
    },
    "github": {"values": ["gV+pU", "TX:W"]},
    "version": {
        "values": [],
        "discovery": {
            "type": "directory_listing",
            "path": "~/.local/share/claude/versions",
        },
    },
    "directory": {
        "values": ["~/Projects/,?;LV_EnYI'.1", "~/Projects/{-B[8]O])^Ga&f"],
        "discovery": {"type": "state_field", "field": "recent_dirs"},
    },
    "mcp": {"values": ["default", "strict"]},
    "permissions": {"values": ["bypass", "default", "plan", "auto"]},
}

DEFAULT_STATE = {
    "last_config": {},
    "recent_dirs": [],
    "launch_count": 0,
}

DEFAULT_THEME_DARK = {
    "name": "dark",
    "global": {
        "bg": None,
        "fg": "#e0e0e0",
        "label_fg": "#888888",
        "separator_fg": "#444444",
        "separator_char": " | ",
        "empty_value_fg": "#555555",
        "empty_value_text": "---",
    },
    "segments": {
        "profile": {
            "value_fg": "#7ec8e3",
            "focus_bg": "#2a2a4e",
            "focus_fg": "#ffffff",
            "option_fg": "#5a8ea3",
        },
        "github": {
            "value_fg": "#a8d8a8",
            "focus_bg": "#2a4e2a",
            "focus_fg": "#ffffff",
            "option_fg": "#6a9a6a",
        },
        "version": {
            "value_fg": "#e8c87e",
            "focus_bg": "#4e4a2a",
            "focus_fg": "#ffffff",
            "option_fg": "#a8984e",
        },
        "directory": {
            "value_fg": "#c8a8e8",
            "focus_bg": "#3a2a4e",
            "focus_fg": "#ffffff",
            "option_fg": "#8a6aa8",
        },
        "mcp": {
            "value_fg": "#e8a88e",
            "focus_bg": "#4e3a2a",
            "focus_fg": "#ffffff",
            "option_fg": "#a87a5e",
        },
        "permissions": {
            "value_fg": "#e88e8e",
            "focus_bg": "#4e2a2a",
            "focus_fg": "#ffffff",
            "option_fg": "#a85e5e",
        },
    },
    "search": {
        "cursor_fg": "#ffffff",
        "match_fg": "#ffff00",
        "no_match_fg": "#ff4444",
    },
}

DEFAULT_THEME_LIGHT = {
    "name": "light",
    "global": {
        "bg": None,
        "fg": "#1a1a1a",
        "label_fg": "#666666",
        "separator_fg": "#cccccc",
        "separator_char": " | ",
        "empty_value_fg": "#aaaaaa",
        "empty_value_text": "---",
    },
    "segments": {
        "profile": {
            "value_fg": "#1a6b8a",
            "focus_bg": "#d0e8f0",
            "focus_fg": "#000000",
            "option_fg": "#4a8ba3",
        },
        "github": {
            "value_fg": "#2a7a2a",
            "focus_bg": "#d0f0d0",
            "focus_fg": "#000000",
            "option_fg": "#4a9a4a",
        },
        "version": {
            "value_fg": "#8a7a1a",
            "focus_bg": "#f0e8d0",
            "focus_fg": "#000000",
            "option_fg": "#a89a4a",
        },
        "directory": {
            "value_fg": "#6a3a8a",
            "focus_bg": "#e8d0f0",
            "focus_fg": "#000000",
            "option_fg": "#8a5aa8",
        },
        "mcp": {
            "value_fg": "#8a5a2a",
            "focus_bg": "#f0e0d0",
            "focus_fg": "#000000",
            "option_fg": "#a87a4a",
        },
        "permissions": {
            "value_fg": "#8a2a2a",
            "focus_bg": "#f0d0d0",
            "focus_fg": "#000000",
            "option_fg": "#a85a5a",
        },
    },
    "search": {
        "cursor_fg": "#000000",
        "match_fg": "#0066cc",
        "no_match_fg": "#cc0000",
    },
}
