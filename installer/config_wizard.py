#!/usr/bin/env python3
"""
Metadelphi Configuration Wizard
A GUI tool for configuring API keys for various LLM providers
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import os
import sys
from pathlib import Path
import webbrowser


class ConfigWizard:
    """Configuration wizard for Metadelphi API keys"""

    # Provider configuration
    PROVIDERS = {
        'MISTRAL': {
            'name': 'Mistral AI',
            'url': 'https://console.mistral.ai/',
            'key_var': 'MISTRAL_API_KEY',
            'base_url_var': None,
            'default_base_url': None,
            'description': 'Mistral AI provides powerful language models'
        },
        'QWEN': {
            'name': 'Alibaba Qwen (DashScope)',
            'url': 'https://dashscope.aliyuncs.com/',
            'key_var': 'QWEN_API_KEY',
            'base_url_var': 'QWEN_BASE_URL',
            'default_base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
            'description': 'Qwen models from Alibaba Cloud'
        },
        'GLM': {
            'name': 'Zhipu GLM',
            'url': 'https://open.bigmodel.cn/',
            'key_var': 'GLM_API_KEY',
            'base_url_var': 'GLM_BASE_URL',
            'default_base_url': 'https://open.bigmodel.cn/api/paas/v4',
            'description': 'GLM models from Zhipu AI'
        },
        'MINIMAX': {
            'name': 'MiniMax',
            'url': 'https://www.minimaxi.com/',
            'key_var': 'MINIMAX_API_KEY',
            'base_url_var': 'MINIMAX_BASE_URL',
            'default_base_url': 'https://api.minimax.io/v1',
            'description': 'MiniMax AI platform'
        },
        'DEEPSEEK': {
            'name': 'DeepSeek',
            'url': 'https://platform.deepseek.com/',
            'key_var': 'DEEPSEEK_API_KEY',
            'base_url_var': 'DEEPSEEK_BASE_URL',
            'default_base_url': 'https://api.deepseek.com',
            'description': 'DeepSeek AI models'
        },
        'OPENAI': {
            'name': 'OpenAI / OpenAI-compatible',
            'url': 'https://platform.openai.com/api-keys',
            'key_var': 'OPENAI_API_KEY',
            'base_url_var': 'OPENAI_BASE_URL',
            'default_base_url': 'https://api.openai.com/v1',
            'description': 'OpenAI GPT models or compatible APIs'
        },
        'GEMINI': {
            'name': 'Google Gemini',
            'url': 'https://makersuite.google.com/app/apikey',
            'key_var': 'GEMINI_API_KEY',
            'base_url_var': 'GEMINI_BASE_URL',
            'default_base_url': 'https://generativelanguage.googleapis.com',
            'description': 'Google Gemini models'
        }
    }

    # MCP Server configuration templates
    MCP_SERVERS = {
        'DASHSCOPE': {
            'name': 'Alibaba Bailian MCP (Web Search)',
            'url': 'https://bailian.console.aliyun.com/',
            'api_key_env': 'DASHSCOPE_API_KEY',
            'servers': [
                {
                    'name': 'web-search',
                    'url': 'https://dashscope.aliyuncs.com/api/v1/mcps/WebSearch/sse',
                    'transport': 'sse'
                },
                {
                    'name': 'web-parser',
                    'url': 'https://dashscope.aliyuncs.com/api/v1/mcps/WebParser/sse',
                    'transport': 'sse'
                }
            ],
            'description': 'Web search and parsing tools via Alibaba Bailian'
        }
    }

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Metadelphi Configuration Wizard")
        self.root.geometry("750x900")
        self.root.resizable(False, False)

        # Configure style
        style = ttk.Style()
        style.theme_use('clam')

        # Store API keys
        self.api_keys = {}
        self.key_entries = {}
        self.mcp_entries = {}  # MCP server configuration entries

        # Load existing configuration if available
        self.load_existing_config()

        # Create UI
        self.create_ui()

    def load_existing_config(self):
        """Load existing configuration from .env file if it exists"""
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            try:
                with open(env_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            self.api_keys[key.strip()] = value.strip()
            except Exception as e:
                print(f"Warning: Could not load existing config: {e}")

    def create_ui(self):
        """Create the user interface"""
        # Header
        header_frame = tk.Frame(self.root, bg='#2c3e50', height=80)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        title_label = tk.Label(
            header_frame,
            text="Metadelphi Configuration",
            font=('Arial', 20, 'bold'),
            bg='#2c3e50',
            fg='white'
        )
        title_label.pack(pady=20)

        # Instructions
        instruction_frame = tk.Frame(self.root, bg='#ecf0f1')
        instruction_frame.pack(fill=tk.X, pady=10)

        instruction_text = tk.Label(
            instruction_frame,
            text="Configure at least one API key to use Metadelphi.\nYou can add more providers later by editing the .env file.",
            font=('Arial', 10),
            bg='#ecf0f1',
            fg='#2c3e50',
            justify=tk.LEFT,
            wraplength=650
        )
        instruction_text.pack(padx=20, pady=10)

        # Scrollable frame for providers
        canvas_frame = tk.Frame(self.root)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        canvas = tk.Canvas(canvas_frame, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='white')

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Add provider configuration sections
        for provider_id, provider_info in self.PROVIDERS.items():
            self.create_provider_section(scrollable_frame, provider_id, provider_info)

        # Add MCP server configuration sections
        self.create_mcp_section(scrollable_frame)

        # Status bar
        self.status_frame = tk.Frame(self.root, bg='#ecf0f1', height=40)
        self.status_frame.pack(fill=tk.X)
        self.status_frame.pack_propagate(False)

        self.status_label = tk.Label(
            self.status_frame,
            text=self.get_status_text(),
            font=('Arial', 10),
            bg='#ecf0f1',
            fg='#2c3e50'
        )
        self.status_label.pack(pady=10)

        # Bottom buttons
        button_frame = tk.Frame(self.root, bg='white')
        button_frame.pack(fill=tk.X, pady=10)

        skip_button = ttk.Button(
            button_frame,
            text="Skip for Now",
            command=self.skip_config,
            width=15
        )
        skip_button.pack(side=tk.LEFT, padx=20)

        save_button = ttk.Button(
            button_frame,
            text="Save Configuration",
            command=self.save_config,
            width=20
        )
        save_button.pack(side=tk.RIGHT, padx=20)

    def create_provider_section(self, parent, provider_id, provider_info):
        """Create a configuration section for a provider"""
        # Provider frame
        provider_frame = tk.LabelFrame(
            parent,
            text=provider_info['name'],
            font=('Arial', 11, 'bold'),
            bg='white',
            padx=10,
            pady=10
        )
        provider_frame.pack(fill=tk.X, padx=10, pady=5)

        # Description
        desc_label = tk.Label(
            provider_frame,
            text=provider_info['description'],
            font=('Arial', 9),
            bg='white',
            fg='#7f8c8d',
            justify=tk.LEFT
        )
        desc_label.pack(anchor=tk.W, pady=(0, 5))

        # API Key entry
        key_frame = tk.Frame(provider_frame, bg='white')
        key_frame.pack(fill=tk.X, pady=5)

        key_label = tk.Label(
            key_frame,
            text="API Key:",
            font=('Arial', 10),
            bg='white',
            width=10,
            anchor=tk.W
        )
        key_label.pack(side=tk.LEFT)

        # Get existing value if available
        existing_value = self.api_keys.get(provider_info['key_var'], '')

        key_entry = tk.Entry(
            key_frame,
            font=('Arial', 10),
            width=50,
            show='*'
        )
        key_entry.insert(0, existing_value)
        key_entry.pack(side=tk.LEFT, padx=5)

        # Store reference
        self.key_entries[provider_info['key_var']] = key_entry

        # Show/Hide button
        show_var = tk.BooleanVar(value=False)

        def toggle_password():
            if show_var.get():
                key_entry.config(show='')
            else:
                key_entry.config(show='*')

        show_button = ttk.Checkbutton(
            key_frame,
            text="Show",
            variable=show_var,
            command=toggle_password,
            width=8
        )
        show_button.pack(side=tk.LEFT)

        # Get API key link
        link_label = tk.Label(
            provider_frame,
            text=f"Get your API key",
            font=('Arial', 9, 'underline'),
            bg='white',
            fg='#3498db',
            cursor='hand2'
        )
        link_label.pack(anchor=tk.W, pady=(0, 5))
        link_label.bind('<Button-1>', lambda e: webbrowser.open(provider_info['url']))

        # Base URL if applicable
        if provider_info['base_url_var']:
            url_frame = tk.Frame(provider_frame, bg='white')
            url_frame.pack(fill=tk.X, pady=5)

            url_label = tk.Label(
                url_frame,
                text="Base URL:",
                font=('Arial', 9),
                bg='white',
                width=10,
                anchor=tk.W
            )
            url_label.pack(side=tk.LEFT)

            existing_url = self.api_keys.get(
                provider_info['base_url_var'],
                provider_info['default_base_url']
            )

            url_entry = tk.Entry(
                url_frame,
                font=('Arial', 9),
                width=50
            )
            url_entry.insert(0, existing_url)
            url_entry.pack(side=tk.LEFT, padx=5)

            # Store reference
            self.key_entries[provider_info['base_url_var']] = url_entry

    def create_mcp_section(self, parent):
        """Create MCP server configuration section."""
        # Separator
        separator = tk.Frame(parent, bg='#bdc3c7', height=2)
        separator.pack(fill=tk.X, padx=10, pady=15)

        # Section header
        header_label = tk.Label(
            parent,
            text="MCP Server Configuration (Optional)",
            font=('Arial', 12, 'bold'),
            bg='white',
            fg='#2c3e50'
        )
        header_label.pack(anchor=tk.W, padx=10, pady=(0, 5))

        desc_label = tk.Label(
            parent,
            text="Configure MCP servers for extended tool capabilities like web search.",
            font=('Arial', 9),
            bg='white',
            fg='#7f8c8d',
            justify=tk.LEFT
        )
        desc_label.pack(anchor=tk.W, padx=10, pady=(0, 10))

        # Default search engine selector
        engine_frame = tk.Frame(parent, bg='white')
        engine_frame.pack(fill=tk.X, padx=10, pady=5)

        engine_label = tk.Label(
            engine_frame,
            text="Default Search Engine:",
            font=('Arial', 10),
            bg='white',
            width=20,
            anchor=tk.W
        )
        engine_label.pack(side=tk.LEFT)

        self.default_engine_var = tk.StringVar(value=self.api_keys.get('DEFAULT_SEARCH_ENGINE', 'bailian'))
        engine_options = ['bailian', 'tavily']
        engine_dropdown = ttk.Combobox(
            engine_frame,
            textvariable=self.default_engine_var,
            values=engine_options,
            state='readonly',
            width=20
        )
        engine_dropdown.pack(side=tk.LEFT, padx=5)

        engine_help = tk.Label(
            parent,
            text="The default engine is used first; the other acts as fallback if configured.",
            font=('Arial', 8),
            bg='white',
            fg='#95a5a6',
            justify=tk.LEFT
        )
        engine_help.pack(anchor=tk.W, padx=10, pady=(0, 10))

        # MCP server frame
        mcp_frame = tk.LabelFrame(
            parent,
            text="Alibaba Bailian MCP (Web Search & Parser)",
            font=('Arial', 11, 'bold'),
            bg='white',
            padx=10,
            pady=10
        )
        mcp_frame.pack(fill=tk.X, padx=10, pady=5)

        # Description
        mcp_desc = tk.Label(
            mcp_frame,
            text="Enable web search and web parsing tools via Alibaba Bailian MCP.",
            font=('Arial', 9),
            bg='white',
            fg='#7f8c8d',
            justify=tk.LEFT
        )
        mcp_desc.pack(anchor=tk.W, pady=(0, 5))

        # API Key entry for DASHSCOPE
        key_frame = tk.Frame(mcp_frame, bg='white')
        key_frame.pack(fill=tk.X, pady=5)

        key_label = tk.Label(
            key_frame,
            text="API Key:",
            font=('Arial', 10),
            bg='white',
            width=10,
            anchor=tk.W
        )
        key_label.pack(side=tk.LEFT)

        existing_value = self.api_keys.get('DASHSCOPE_API_KEY', '')

        key_entry = tk.Entry(
            key_frame,
            font=('Arial', 10),
            width=50,
            show='*'
        )
        key_entry.insert(0, existing_value)
        key_entry.pack(side=tk.LEFT, padx=5)

        # Store reference
        self.mcp_entries['DASHSCOPE_API_KEY'] = key_entry

        # Show/Hide button
        show_var = tk.BooleanVar(value=False)

        def toggle_password():
            if show_var.get():
                key_entry.config(show='')
            else:
                key_entry.config(show='*')

        show_button = ttk.Checkbutton(
            key_frame,
            text="Show",
            variable=show_var,
            command=toggle_password,
            width=8
        )
        show_button.pack(side=tk.LEFT)

        # Get API key link
        link_label = tk.Label(
            mcp_frame,
            text="Get your API key from Alibaba Bailian Console",
            font=('Arial', 9, 'underline'),
            bg='white',
            fg='#3498db',
            cursor='hand2'
        )
        link_label.pack(anchor=tk.W, pady=(0, 5))
        link_label.bind('<Button-1>', lambda e: webbrowser.open('https://bailian.console.aliyun.com/'))

        # Tavily SDK frame
        tavily_frame = tk.LabelFrame(
            parent,
            text="Tavily SDK (Web Search)",
            font=('Arial', 11, 'bold'),
            bg='white',
            padx=10,
            pady=10
        )
        tavily_frame.pack(fill=tk.X, padx=10, pady=5)

        # Description
        tavily_desc = tk.Label(
            tavily_frame,
            text="Enable native web search, extract, crawl, and map tools via Tavily SDK.",
            font=('Arial', 9),
            bg='white',
            fg='#7f8c8d',
            justify=tk.LEFT
        )
        tavily_desc.pack(anchor=tk.W, pady=(0, 5))

        # API Key entry for Tavily
        tavily_key_frame = tk.Frame(tavily_frame, bg='white')
        tavily_key_frame.pack(fill=tk.X, pady=5)

        tavily_key_label = tk.Label(
            tavily_key_frame,
            text="API Key:",
            font=('Arial', 10),
            bg='white',
            width=10,
            anchor=tk.W
        )
        tavily_key_label.pack(side=tk.LEFT)

        tavily_existing_value = self.api_keys.get('TAVILY_API_KEY', '')

        tavily_key_entry = tk.Entry(
            tavily_key_frame,
            font=('Arial', 10),
            width=50,
            show='*'
        )
        tavily_key_entry.insert(0, tavily_existing_value)
        tavily_key_entry.pack(side=tk.LEFT, padx=5)

        # Store reference
        self.mcp_entries['TAVILY_API_KEY'] = tavily_key_entry

        # Show/Hide button for Tavily
        tavily_show_var = tk.BooleanVar(value=False)

        def toggle_tavily_password():
            if tavily_show_var.get():
                tavily_key_entry.config(show='')
            else:
                tavily_key_entry.config(show='*')

        tavily_show_button = ttk.Checkbutton(
            tavily_key_frame,
            text="Show",
            variable=tavily_show_var,
            command=toggle_tavily_password,
            width=8
        )
        tavily_show_button.pack(side=tk.LEFT)

        # Get Tavily API key link
        tavily_link_label = tk.Label(
            tavily_frame,
            text="Get your API key from Tavily Console",
            font=('Arial', 9, 'underline'),
            bg='white',
            fg='#3498db',
            cursor='hand2'
        )
        tavily_link_label.pack(anchor=tk.W, pady=(0, 5))
        tavily_link_label.bind('<Button-1>', lambda e: webbrowser.open('https://app.tavily.com/'))

        # Tool Concurrency setting
        concurrency_frame = tk.Frame(mcp_frame, bg='white')
        concurrency_frame.pack(fill=tk.X, pady=5)

        concurrency_label = tk.Label(
            concurrency_frame,
            text="Max Parallel Tools:",
            font=('Arial', 9),
            bg='white',
            width=15,
            anchor=tk.W
        )
        concurrency_label.pack(side=tk.LEFT)

        existing_concurrency = self.api_keys.get('MAX_TOOL_CONCURRENCY', '5')

        concurrency_entry = tk.Entry(
            concurrency_frame,
            font=('Arial', 9),
            width=10
        )
        concurrency_entry.insert(0, existing_concurrency)
        concurrency_entry.pack(side=tk.LEFT, padx=5)

        # Store reference
        self.mcp_entries['MAX_TOOL_CONCURRENCY'] = concurrency_entry

        # Help text
        help_label = tk.Label(
            concurrency_frame,
            text="(1-10, controls how many tools run simultaneously)",
            font=('Arial', 8),
            bg='white',
            fg='#95a5a6'
        )
        help_label.pack(side=tk.LEFT, padx=5)

    def get_status_text(self):
        """Get status text showing how many providers are configured"""
        configured = sum(
            1 for provider_info in self.PROVIDERS.values()
            if self.key_entries.get(provider_info['key_var'], None) and
            self.key_entries[provider_info['key_var']].get().strip() and
            self.key_entries[provider_info['key_var']].get().strip() not in ['your_', '']
        )
        return f"Status: {configured}/{len(self.PROVIDERS)} providers configured"

    def save_config(self):
        """Save configuration to .env file"""
        # Collect all entries
        config_data = {}
        has_valid_key = False

        for key_var, entry in self.key_entries.items():
            value = entry.get().strip()
            if value and not value.startswith('your_'):
                config_data[key_var] = value
                # Check if this is an API key (not a base URL)
                if key_var.endswith('_API_KEY'):
                    has_valid_key = True

        # Collect MCP configuration entries
        mcp_config_data = {}
        for key_var, entry in self.mcp_entries.items():
            value = entry.get().strip()
            if value:
                mcp_config_data[key_var] = value

        # Treat Tavily key as a valid key as well
        if 'TAVILY_API_KEY' in mcp_config_data:
            has_valid_key = True

        # Validate at least one API key is configured
        if not has_valid_key:
            messagebox.showwarning(
                "No API Keys Configured",
                "Please configure at least one API key to use Metadelphi.\n\n"
                "You can click 'Skip for Now' if you want to configure later."
            )
            return

        # Save to .env file
        env_path = Path(__file__).parent.parent / ".env"

        try:
            with open(env_path, 'w') as f:
                f.write("# Metadelphi API Configuration\n")
                f.write("# Generated by Configuration Wizard\n\n")

                # Write configuration for each provider
                for provider_id, provider_info in self.PROVIDERS.items():
                    key_var = provider_info['key_var']

                    if key_var in config_data:
                        f.write(f"# {provider_info['name']}\n")
                        f.write(f"{key_var}={config_data[key_var]}\n")

                        # Write base URL if applicable
                        if provider_info['base_url_var']:
                            base_url_var = provider_info['base_url_var']
                            if base_url_var in config_data:
                                f.write(f"{base_url_var}={config_data[base_url_var]}\n")

                        f.write("\n")

                # Write Web Search configuration
                f.write("# Web Search Configuration\n")
                default_engine = self.default_engine_var.get().strip().lower()
                if default_engine in ['bailian', 'tavily']:
                    f.write(f"DEFAULT_SEARCH_ENGINE={default_engine}\n")
                if 'TAVILY_API_KEY' in mcp_config_data:
                    f.write(f"TAVILY_API_KEY={mcp_config_data['TAVILY_API_KEY']}\n")
                f.write("\n")

                # Write MCP server configuration
                if mcp_config_data:
                    f.write("# MCP Server Configuration\n")
                    if 'DASHSCOPE_API_KEY' in mcp_config_data:
                        f.write(f"DASHSCOPE_API_KEY={mcp_config_data['DASHSCOPE_API_KEY']}\n")
                    if 'MAX_TOOL_CONCURRENCY' in mcp_config_data:
                        f.write(f"MAX_TOOL_CONCURRENCY={mcp_config_data['MAX_TOOL_CONCURRENCY']}\n")
                    f.write("\n")

            messagebox.showinfo(
                "Configuration Saved",
                f"Configuration saved successfully!\n\n"
                f"{len([k for k in config_data.keys() if k.endswith('_API_KEY')])} API key(s) configured.\n\n"
                f"You can edit the configuration later by editing:\n{env_path}"
            )
            self.root.quit()

        except Exception as e:
            messagebox.showerror(
                "Save Error",
                f"Failed to save configuration:\n{str(e)}"
            )

    def skip_config(self):
        """Skip configuration for now"""
        result = messagebox.askyesno(
            "Skip Configuration",
            "Are you sure you want to skip configuration?\n\n"
            "You will need to manually configure API keys in the .env file\n"
            "before you can use Metadelphi."
        )

        if result:
            # Create empty .env file with template
            env_path = Path(__file__).parent.parent / ".env"
            template_path = Path(__file__).parent.parent / ".env.template"

            if template_path.exists() and not env_path.exists():
                try:
                    import shutil
                    shutil.copy(template_path, env_path)
                except Exception:
                    pass

            self.root.quit()

    def run(self):
        """Run the configuration wizard"""
        self.root.mainloop()


def main():
    """Main entry point"""
    try:
        wizard = ConfigWizard()
        wizard.run()
        return 0
    except KeyboardInterrupt:
        print("\nConfiguration cancelled by user")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
