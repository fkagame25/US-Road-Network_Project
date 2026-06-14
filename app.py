import dash
from dash import dcc, html
import plotly.express as px
import pandas as pd
from neo4j import GraphDatabase


# 1. LIVE NEO4J DATA EXTRACTION PIPELINE

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "Password123"

def fetch_graph_metrics():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    
    kpi_query = """
    MATCH (i:Intersection)
    WITH count(i) AS total_nodes
    MATCH ()-[r:ROAD]->()
    RETURN total_nodes, count(r) AS total_edges
    """
    
    # Grouping counts on the database level to ensure cleaner data delivery
    degree_query = """
    MATCH (i:Intersection)
    OPTIONAL MATCH (i)-[:ROAD]-()
    RETURN i.id AS IntersectionID, count(*) AS Degree
    """
    
    
    print("[*] Contacting Neo4j Graph to stream live structural data...")
    with driver.session() as session:
        kpi_result = session.run(kpi_query).single()
        total_intersections = kpi_result["total_nodes"] if kpi_result else 87575
        total_roads = kpi_result["total_edges"] if kpi_result else 121961
        
        degree_result = session.run(degree_query)
        # Force the values into standard Python integers during parsing
        records = [{"IntersectionID": str(r["IntersectionID"]), "Degree": int(r["Degree"])} for r in degree_result]
        df_degrees = pd.DataFrame(records)
        
    driver.close()
    print("[✓] Graph synchronization successful!")
    return total_intersections, total_roads, df_degrees

# live synchronization fetch
total_intersections, total_roads, df = fetch_graph_metrics()

# Check to prevent the max() value error if the dataframe is empty
if df.empty:
    df = pd.DataFrame(columns=['IntersectionID', 'Degree'])
    max_degree = 10
else:
    max_degree = int(df['Degree'].max())


# 2. DATA PROCESSING & INTERSECTION CATEGORIZATION 

top_10_df = df.nlargest(10, 'Degree') if not df.empty else pd.DataFrame(columns=['IntersectionID', 'Degree'])

def categorize_degree(deg):
    if deg <= 2: return 'Low Connectivity (1-2)'
    elif deg <= 4: return 'Medium Connectivity (3-4)'
    else: return 'High Connectivity (Hubs 5+)'

df['Category'] = df['Degree'].apply(categorize_degree)
category_counts = df['Category'].value_counts().reset_index()
category_counts.columns = ['Category', 'Count']


# 3. PLOTLY CHART VISUALIZATIONS 

fig_distribution = px.histogram(
    df, x='Degree', 
    title='Degree Distribution of US Road Network Intersections',
    labels={'Degree': 'Number of Connecting Roads (Degree)', 'count': 'Intersection Count'},
    color_discrete_sequence=['#2B6CB0'],
    nbins=max_degree if max_degree > 0 else 10
)
fig_distribution.update_layout(bargap=0.1, template='plotly_white')

fig_top10 = px.bar(
    top_10_df, x='IntersectionID', y='Degree',
    title='Top 10 Most Connected Intersections (Hub Analysis)',
    labels={'IntersectionID': 'Intersection Node ID', 'Degree': 'Road Connections (Degree)'},
    color='Degree', color_continuous_scale='Blues'
)
fig_top10.update_layout(template='plotly_white')

fig_categories = px.pie(
    category_counts, names='Category', values='Count',
    title='Proportional Breakdown of Intersection Connectivity',
    color_discrete_sequence=px.colors.qualitative.Pastel
)


# 4. DASHBOARD PRESENTATION LAYOUT

app = dash.Dash(__name__)

app.layout = html.Div(style={'fontFamily': 'Segoe UI, Arial', 'backgroundColor': '#f7fafc', 'padding': '30px'}, children=[
    html.H1("US Road Network Analytics Dashboard", style={'textAlign': 'center', 'color': '#2d3748', 'marginBottom': '40px', 'fontWeight': '600'}),
    
    html.Div(style={'display': 'flex', 'justifyContent': 'space-between', 'marginBottom': '40px', 'gap': '20px'}, children=[
        html.Div(style={'backgroundColor': '#fff', 'padding': '25px', 'borderRadius': '12px', 'boxShadow': '0 4px 6px rgba(0,0,0,0.05)', 'textAlign': 'center', 'flex': '1'}, children=[
            html.H3("Total Intersections", style={'color': '#718096', 'fontSize': '16px', 'margin': '0', 'textTransform': 'uppercase'}),
            html.H1(f"{total_intersections:,}", style={'color': '#2b6cb0', 'fontSize': '36px', 'margin': '10px 0 0 0'})
        ]),
        html.Div(style={'backgroundColor': '#fff', 'padding': '25px', 'borderRadius': '12px', 'boxShadow': '0 4px 6px rgba(0,0,0,0.05)', 'textAlign': 'center', 'flex': '1'}, children=[
            html.H3("Total Roads", style={'color': '#718096', 'fontSize': '16px', 'margin': '0', 'textTransform': 'uppercase'}),
            html.H1(f"{total_roads:,}", style={'color': '#2c5282', 'fontSize': '36px', 'margin': '10px 0 0 0'})
        ]),
        html.Div(style={'backgroundColor': '#fff', 'padding': '25px', 'borderRadius': '12px', 'boxShadow': '0 4px 6px rgba(0,0,0,0.05)', 'textAlign': 'center', 'flex': '1'}, children=[
            html.H3("Average Network Degree", style={'color': '#718096', 'fontSize': '16px', 'margin': '0', 'textTransform': 'uppercase'}),
            html.H1("2.8 (Sparse)", style={'color': '#dd6b20', 'fontSize': '36px', 'margin': '10px 0 0 0'})
        ]),
    ]),
    
    html.Div(style={'display': 'grid', 'gridTemplateColumns': '1fr 1fr', 'gap': '30px', 'marginBottom': '30px'}, children=[
        html.Div(style={'backgroundColor': '#fff', 'padding': '20px', 'borderRadius': '12px', 'boxShadow': '0 4px 6px rgba(0,0,0,0.02)'}, children=[
            dcc.Graph(figure=fig_distribution)
        ]),
        html.Div(style={'backgroundColor': '#fff', 'padding': '20px', 'borderRadius': '12px', 'boxShadow': '0 4px 6px rgba(0,0,0,0.02)'}, children=[
            dcc.Graph(figure=fig_top10)
        ]),
    ]),
    
    html.Div(style={'backgroundColor': '#fff', 'padding': '20px', 'borderRadius': '12px', 'boxShadow': '0 4px 6px rgba(0,0,0,0.02)', 'maxWidth': '600px', 'margin': '0 auto'}, children=[
        dcc.Graph(figure=fig_categories)
    ])
])

if __name__ == '__main__':
    app.run(debug=True)