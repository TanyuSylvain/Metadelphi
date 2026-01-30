"""
Text processing utilities for LLM response handling.
"""

import re


class TextProcessor:
    """Utility class for processing text from LLM responses."""

    @staticmethod
    def convert_math_delimiters(text: str) -> str:
        """
        Convert LaTeX math delimiters to standard format.

        Converts \\[ \\] to $$ $$ (display math) and \\( \\) to $ $ (inline math).
        This ensures compatibility with frontend KaTeX rendering.

        Args:
            text: Text containing math expressions

        Returns:
            str: Text with converted delimiters
        """
        # Convert display math \[ \] to $$ $$
        text = re.sub(r'\\\[([\s\S]*?)\\\]', r'$$\1$$', text)
        # Convert inline math \( \) to $ $
        text = re.sub(r'\\\((.*?)\\\)', r'$\1$', text)
        return text

    @staticmethod
    def extract_text_content(content) -> str:
        """
        Extract text from content which can be either a string or list of blocks.

        Args:
            content: Either a string or list of content blocks (for thinking models)

        Returns:
            str: Extracted text content
        """
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            # Content is a list of blocks (common for thinking/reasoning models)
            text_parts = []
            for block in content:
                if isinstance(block, dict):
                    # Extract text from various possible formats
                    if 'text' in block:
                        text_parts.append(block['text'])
                    elif 'content' in block:
                        text_parts.append(block['content'])
                elif isinstance(block, str):
                    text_parts.append(block)
            return ''.join(text_parts)
        return ""
