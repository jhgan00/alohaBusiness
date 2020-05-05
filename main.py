#-*- coding:utf-8 -*-
# data handling
import pandas as pd
import numpy as np
import json
from sklearn.preprocessing import MinMaxScaler

# maps
# import googlemaps
import folium
from folium import plugins
from pyproj import Proj, transform

# dash app
import dash
import dash_table
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input,Output

# dash plot
import chart_studio.plotly as plotly
import plotly.express as px
import plotly.graph_objects as go
import flask

server = flask.Flask(__name__)
app = dash.Dash(__name__, server=server)

# def base RP function
def calcRP(data, age, sex, weight, survival):
    if (age=='상관없음')&(sex=='상관없음'):
        weightedSum = data.USE_AMT.mean()
        return weightedSum*survival
    elif (age=='상관없음'):
        target, nontarget = data[data.SEX_CD==sex], data[data.SEX_CD!=sex]
        n = 2
    elif (sex=='상관없음'):	
        target, nontarget = data[data.AGE_CD==age], data[data.AGE_CD!=age]
        n = 10
    else:
        target, nontarget = data[(data.AGE_CD==age)&(data.SEX_CD==sex)], data[(data.AGE_CD!=age)|(data.SEX_CD!=sex)]
        n = 20
    target = target.USE_AMT.sum() * weight
    nontarget = nontarget.USE_AMT.sum() * (1-weight) / (n-1)
    weightedSum = target + nontarget
    RP = weightedSum* survival
    return RP

# def update RP function
def updateRP(data, category, age, sex, weight):
    filtered_df = data[data.MCT_CAT_CD==category]
    survival = 0.8
    RPtable = filtered_df.groupby("DONG_CD").apply(calcRP, age=age, sex=sex, weight=weight, survival=survival).reset_index().rename(columns={0:"RP"})
    # minmax scaling
    RPtable["RP"] = MinMaxScaler((0,100)).fit_transform(RPtable.RP.values.reshape((-1,1)))
    return RPtable

# read data
print("Reading data ...")
data = pd.read_csv("data/shinhan_dash.csv").astype({"AGE_CD":"str", "DONG_CD":"str",  "MCT_CAT_CD":"str"})
barplot = pd.read_csv("data/shinhan_barplot.csv").astype({"AGE_CD":"str", "DONG_CD":"str",  "MCT_CAT_CD":"str"})
tsplot = pd.read_csv("data/shinhan_tsplot.csv").astype({"DONG_CD":"str",  "MCT_CAT_CD":"str"})

# 서울시 경계 파일
seoul = json.load(open("data/seoul.json"))
polygons = folium.features.GeoJson(seoul)
print("Done")


colors = {"background":"#17202A", "text":"#FFFFFF"}


app.layout = html.Div([
    html.H1('Aloha Dashboard | 서대문구/마포구 창업 의사결정 도우미'),
    dcc.Tabs(
    	id="tabs-example",
    	value='tab-1-example',
    	children=[
        dcc.Tab(
        	label='Overview',
        	value='tab-1-example',
        	children=[
        	html.Div(
        	className = "outline",
			children = [
			html.Div(className="row",
				children=[
				html.Div(
					className="column left",
					children = [
					html.Div(html.Label("1) 업종을 선택해주세요", className='label', style={'font-family':'나눔스퀘어라운드 Light'})),
					dcc.Dropdown(
						className='dropdown',
						id='category',
						options = [{'label':k,'value':k} for k in data.MCT_CAT_CD.unique()],
						placeholder="업종을 선택해주세요"),
					html.Div(html.Label("2) 타겟 연령대를 선택해주세요", className='label', style={'font-family':'나눔스퀘어라운드 Light'})),
					dcc.Dropdown(
						className='dropdown',
						id='age',
						options = [{'label':"상관없음", 'value':'상관없음'}]+ [{'label':k,'value':k} for k in data.AGE_CD.unique()],
						placeholder="타겟 연령대를 선택해주세요"),
					html.Div(html.Label("3) 타겟 성별을 선택해주세요", className='label', style={'font-family':'나눔스퀘어라운드 Light'})),
					dcc.Dropdown(
						className='dropdown',
						id='sex',
						options = [{'label':"상관없음", 'value':'상관없음'}, {'label':"남성",'value':"A"}, {'label':"여성",'value':"B"}],
						placeholder="타겟 성별을 선택해주세요"),
					html.Div(html.Label("4) 타겟 가중치를 입력해주세요(0~1)", className='label', style={'font-family':'나눔스퀘어라운드 Light'})),
					dcc.Input(
						className='Input',
						id='weight',
						placeholder="0에서 1 사이의 숫자를 입력해주세요"),
					html.Div(className='textbox', id='agesex'),
					html.Div(className='textbox', id='cat'),
					html.Div(className='textbox', id='loc')
					]),

				html.Div(
					className='column right',
					children=[
					html.Iframe(
						className='plot',
						id='map',
						style={"height":"450px"})])
				])
			])
			]),
        dcc.Tab(
        	label='지역별 비교',
        	value='tab-2-example',
        	children=[
        	html.Div(
        		className='row',
        		children=[
        		html.Div(
        			className='column left',
        			children=[
        			html.Div(html.Label("관심 지역을 선택해주세요", className='label', style={'font-family':'나눔스퀘어라운드 Light'})),
        			dcc.Dropdown(
        				className='dropdown',
        				id='location',
        				options = [{"label":location,"value":location} for location in data.DONG_CD.unique()],
        				placeholder="관심 지역을 선택해주세요"),
        			dcc.Graph(
        				className='plot',
        				id='scoreplot',
        				style={"height":"500px", "width":"100%"})
        			]),
        		html.Div(
        			className='column right',
        			children=[
        			dcc.Graph(
        				className='plot',
        				id='tsplot',
        				style={"height":"500px", "width":"100%"}),
        			dcc.Graph(
        				className='plot',
        				id='barplot',
        				style={"width":"100%"})
        			])
        		])
        	])
    ]),
    html.Div(id='tabs-content-example')
])

@app.callback(
	[Output('agesex','children'),
	Output('cat','children'),
	Output('loc','children'),
	Output(component_id='map', component_property='srcDoc'),
	Output('scoreplot', 'figure')],
    [Input(component_id='category', component_property='value'),
    Input(component_id='sex', component_property='value'),
    Input(component_id='age', component_property='value'),
    Input(component_id='weight', component_property='value')]
)
def update_RP(category, sex, age, weight):   
	lat, lon = 37.5534566, 126.9231184
	googlemap = folium.Map(location=[lat,lon], zoom_start=13.5)
	plugins.ScrollZoomToggler().add_to(googlemap)

	if None in [category, sex, age]:
		googlemap.add_child(polygons)
		agesextext, cattext, loctext, fig= None, None, None, None
	
	else:
		try:
			if (age=='상관없음')&(sex=='상관없음'):
				weight=0.05
			
			weight = float(weight)
			
			RP = updateRP(data, category, age, sex, weight)

			googlemap.choropleth(
				geo_data="data/seoul.json",
				data=RP,
				columns=['DONG_CD', 'RP'],
				key_on='feature.id',
				fill_color='RdYlGn',
				legend_name='창업 추천 지수')

			bestlocation = RP[RP.RP==max(RP.RP)].DONG_CD.values[0]
			bestscore = max(RP.RP)
			
			fig = go.Figure(
				go.Bar(y=RP.sort_values("RP").DONG_CD, x=RP.sort_values("RP").RP, orientation='h'),
				layout={"plot_bgcolor":colors['background'], 'paper_bgcolor':colors['background']})

			fig.update_layout(title = "%s 업종의 추천지수" %category, font=dict(family='NanumGothic',size=13, color=colors['text']))

			if (age=='상관없음')&(sex=='상관없음'):
				agesextext=None
			elif age == "상관없음":
				if sex=='M':
					agesextext = "남성을 타게팅한"
				else:
					agesextext = "여성을 타게팅한"
			elif sex == "상관없음":
					agesextext = "%s 세를 타게팅한" %age
			
			else:
				if sex=='M':
					sextext = "남성"
				else:
					sextext = "여성"
				agesextext = "%s 세 %s 을 타게팅한" %(age,sextext)
			loctext = "%s 입니다." %bestlocation	
			cattext = "%s 업종의 추천 지역은" %category

		except:
			googlemap.add_child(polygons)
			agesextext, cattext, loctext, fig = None, None, None, None

	googlemap = googlemap.get_root().render()
	return agesextext, cattext, loctext, googlemap, fig


# 성별 매출액 그래프
@app.callback(
    [Output(component_id='tsplot', component_property='figure'),
    Output(component_id='barplot', component_property='figure')],
    [Input(component_id='category', component_property='value'),
    Input(component_id='location', component_property='value')]
    )
def update_plot(category,location):
	if (category == None) or (location == None): title1, title2 = "매출액 추이","성별/연령대별 매출액"
	else:
		title1 = '%s %s 업종 매출액 추이' %(location, category) 
		title2 = "%s %s 업종 성별/연령대별 매출액" %(location, category)
	
	# filter data
	filtered_df = tsplot[(tsplot.MCT_CAT_CD == category)]

	# draw fig
	fig1 = go.Figure(layout={'paper_bgcolor':colors['background']})
	annotations = []

	for loc in filtered_df.DONG_CD.unique():
	    if loc == location:
	        label, opacity, linewidth = loc, 1, 4
	    else:
	        label, opacity, linewidth = "", 0.3, 2
	    tmp = filtered_df[filtered_df.DONG_CD==loc]
	    
	    fig1.add_trace(
	        go.Scatter(
	            x=tmp.STD_DD,
	            y=tmp.USE_AMT,
	            mode='lines+markers',
	            name= loc,
	            line=dict(width=linewidth),
	            opacity=opacity))

	fig1.update_layout(
		title = title1,
		xaxis=dict(showgrid=False, linecolor='rgb(204, 204, 204)'),
    	yaxis = dict(title='매출액', linecolor='rgb(204, 204, 204)'),
    	font=dict(family='NanumGothic',size=13, color=colors['text']),
    	annotations=annotations,
    	showlegend=True
    	)

	filtered_df = barplot[(barplot.MCT_CAT_CD==category)&(barplot.DONG_CD==location)]

	fig2 = go.Figure(
		data = [go.Bar(x=filtered_df[filtered_df.SEX_CD=="A"].AGE_CD, y=filtered_df[filtered_df.SEX_CD=='A'].USE_AMT, name="남성"),
		go.Bar(x=filtered_df[filtered_df.SEX_CD=="B"].AGE_CD, y=filtered_df[filtered_df.SEX_CD=='B'].USE_AMT, name="여성")],
		layout={"plot_bgcolor":colors['background'], 'paper_bgcolor':colors['background']})


	fig2.update_layout(
		title = title2,
		xaxis_title = '연령대',
    	yaxis_title = '매출액',
    	barmode='group',
    	font=dict(family='NanumGothic',size=13, color=colors['text'])
    	)
	return fig1, fig2	

if __name__ == '__main__':
	app.run_server(host='0.0.0.0', port=8080, debug=False)