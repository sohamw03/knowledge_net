from langchain_core.tools import tool

@tool
def calc(a: int, b: int) -> int:
    """
    Takes in two integers and returns their integer sum.
    """
    return str(a + b)
