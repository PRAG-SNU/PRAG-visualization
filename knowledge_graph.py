import dash
from dash import html, dcc
import dash_cytoscape as cyto
import dash_daq as daq
from dash.dependencies import Input, Output, State

app = dash.Dash(__name__)

# -----------------------------------------------------------
# Place your node information here:
# nodes = [
#     {
#         "data": {"id": "Photosynthesis", "label": "Photosynthesis"},
#         "position": {"x": 0, "y": 0}
#     },
#     {
#         "data": {"id": "Rubisco", "label": "Rubisco"},
#         "position": {"x": 200, "y": 200}
#     }
#     ...
# ]
#
# Place your edge information here:
# edges = [
#     {
#         "data": {"source": "Photosynthesis", "target": "Rubisco", "label": "INVOLVES"}
#     }
#     ...
# ]
# -----------------------------------------------------------

nodes = []
edges = []

# Initialize default styles for each node (this dictionary will be updated dynamically)
default_styles = {
    node['data']['id']: {
        'width': 50,
        'height': 50,
        'font-size': 12,
        'background-color': '#87D88B',
        'color': '#FFFFFF',
        'text-outline-color': '#0074D9'
    } 
    for node in nodes
}

app.layout = html.Div([
    # Store for persisting node style data
    dcc.Store(id='styles-store', data=default_styles),
    
    # Left control panel
    html.Div([
        html.Label("Apply to All Nodes:"),
        dcc.RadioItems(
            id='apply-all',
            options=[
                {'label': 'Yes', 'value': 'yes'},
                {'label': 'No', 'value': 'no'}
            ],
            value='yes',
            labelStyle={'display': 'inline-block'}
        ),
        html.Br(),
        
        html.Label("Node Size:"),
        dcc.Slider(
            id='node-size-slider',
            min=10,
            max=120,
            step=5,
            value=50,
            marks={i: str(i) for i in range(10, 121, 10)}
        ),
        
        html.Label("Font Size:"),
        dcc.Slider(
            id='font-size-slider',
            min=10,
            max=30,
            step=1,
            value=12,
            marks={i: str(i) for i in range(10, 31, 5)}
        ),
        
        html.Label("Node Color:"),
        daq.ColorPicker(
            id='node-color-picker',
            value={'hex': '#87D88B'}
        ),
        
        html.Label("Font Color:"),
        daq.ColorPicker(
            id='font-color-picker',
            value={'hex': '#FFFFFF'}
        ),
        
        html.Label("Font Outline Color:"),
        daq.ColorPicker(
            id='font-outline-color-picker',
            value={'hex': '#0074D9'}
        ),
        html.Br(),
        
        html.Label("Select Node:"),
        dcc.Dropdown(
            id='node-selector',
            # Options will be dynamically updated if you add nodes
            options=[{'label': node['data']['label'], 'value': node['data']['id']} for node in nodes],
            value=None,
            disabled=False
        )
    ], style={'width': '20%', 'float': 'left', 'padding': '20px'}),
    
    # Cytoscape graph
    html.Div([
        cyto.Cytoscape(
            id='cytoscape',
            elements=nodes + edges,
            style={'width': '100%', 'height': '600px'},
            layout={'name': 'preset'},
        )
    ], style={'width': '75%', 'float': 'right', 'padding': '20px'}),
    
    # Button and storage for saving as PNG
    html.Button("Save Graph as PNG", id="save-button", n_clicks=0),
    dcc.Store(id="image-data"),
    dcc.Download(id="download")
])

@app.callback(
    [Output('cytoscape', 'stylesheet'),
     Output('styles-store', 'data')],
    [
        Input('apply-all', 'value'),
        Input('node-size-slider', 'value'),
        Input('font-size-slider', 'value'),
        Input('node-color-picker', 'value'),
        Input('font-color-picker', 'value'),
        Input('font-outline-color-picker', 'value'),
        Input('node-selector', 'value')
    ],
    [State('styles-store', 'data')]
)
def update_stylesheet(
    apply_all,
    node_size,
    font_size,
    node_color,
    font_color,
    font_outline_color,
    selected_node,
    styles
):
    """
    Updates the stylesheet for Cytoscape based on user inputs (size, colors, etc.).
    If 'apply-all' is 'yes', all nodes are updated. Otherwise, only the selected node is updated.
    """
    if not nodes:
        # If no nodes are defined, return empty stylesheet
        return [], styles
    
    if apply_all == 'yes':
        for node_id in styles:
            styles[node_id] = {
                'width': node_size,
                'height': node_size,
                'font-size': font_size,
                'background-color': node_color['hex'],
                'color': font_color['hex'],
                'text-outline-color': font_outline_color['hex']
            }
    else:
        # Update only the selected node (if it exists in styles)
        if selected_node in styles:
            styles[selected_node] = {
                'width': node_size,
                'height': node_size,
                'font-size': font_size,
                'background-color': node_color['hex'],
                'color': font_color['hex'],
                'text-outline-color': font_outline_color['hex']
            }

    # Construct the new stylesheet
    stylesheet = [
        {
            'selector': f'node[id="{node_id}"]',
            'style': {
                'width': styles[node_id]['width'],
                'height': styles[node_id]['height'],
                'font-size': styles[node_id]['font-size'],
                'background-color': styles[node_id]['background-color'],
                'color': styles[node_id]['color'],
                'content': 'data(label)',
                'text-valign': 'center',
                'text-outline-width': 0,
                'text-outline-color': styles[node_id]['text-outline-color'],
                'text-wrap': 'wrap',
                'text-max-width': styles[node_id]['width'] - 10
            }
        }
        for node_id in styles
    ]
    
    stylesheet.append({
        'selector': 'edge',
        'style': {
            'width': 2,
            'line-color': 'gray',
            'curve-style': 'bezier',
            'target-arrow-color': 'gray',
            'target-arrow-shape': 'triangle',
            'label': 'data(label)',
            'text-rotation': 'autorotate',
            'font-size': 10,
            'color': 'black',
            'text-background-opacity': 1,
            'text-background-color': 'white',
            'text-background-padding': 2
        }
    })
    
    return stylesheet, styles

# Client-side callback to download the graph as a PNG
app.clientside_callback(
    """
    function(n_clicks) {
        if (n_clicks > 0) {
            var cy = document.getElementById('cytoscape')._cyreg.cy;
            var png64 = cy.png({bg: 'white', scale: 4, full: true});
            var a = document.createElement('a');
            a.href = png64;
            a.download = 'graph.png';
            a.click();
        }
        return '';
    }
    """,
    Output("image-data", "data"),
    Input("save-button", "n_clicks")
)

if __name__ == '__main__':
    app.run_server(debug=True, port=8050)
