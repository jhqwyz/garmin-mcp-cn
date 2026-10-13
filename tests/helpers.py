"""Read text from both legacy and current FastMCP convenience return values."""
def tool_text(result):
    content = result[0] if isinstance(result, tuple) else result
    return content[0].text
