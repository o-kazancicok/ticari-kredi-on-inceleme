"""Optional, local stdio MCP adapter. Not required by the web demo."""
from fastmcp import FastMCP
from kredi.seed import seed
from kredi import storage
from kredi.policy import search_policy
from kredi.tools import ReviewTools

mcp = FastMCP('Sentetik Ticari Kredi Ön İnceleme')


@mcp.tool
def get_demo_application(application_id: str) -> dict:
    """Get one synthetic application; accepted IDs are 1001 through 1005."""
    app = storage.get_application(application_id)
    return {k: v for k, v in app.items() if k not in ('customer', 'customer_service_error')}


@mcp.tool
def search_demo_policy(query: str) -> list:
    """Retrieve fictional product policy clauses by local keyword overlap."""
    return search_policy(query)


@mcp.tool
def run_precheck_group(application_id: str, group: str) -> list:
    """Run identity, activity, contact, guarantor or documents checks with source evidence."""
    tools = ReviewTools(application_id)
    for name in ['get_application', 'get_customer', 'get_documents', 'get_policy']:
        tools.call(name)
    return tools.call('check_' + group)


if __name__ == '__main__':
    seed()
    mcp.run(transport='stdio')
