import streamlit as st
import pandas as pd
import numpy as np
import shioaji as sj
import datetime
import mplfinance as mpf
import matplotlib.pyplot as plt
#import mplcursors
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
#import talib

# 登录Shioaji API
api = sj.Shioaji(simulation=True)
api.login(
    api_key="7zS8VqpPWfR6rpPxLa9qQv25UtDeE7RJGNgEQnXaMfgS", 
    secret_key="Hqo1YvabcWU9LF7uuqbAJdSdXFuaemptDSPRV69BFJsL",
    contracts_timeout=10000  # 设置合约下载超时时间为10秒钟
)

# Streamlit页面标题
st.title("股票分析")

# 股票选择框
option = st.selectbox(
    '选择股票',
    ['2330', '2884']
)

today = datetime.date.today()
season_ago = (today - datetime.timedelta(days=90))
for_caculate = (today - datetime.timedelta(days=180))

# 获取历史数据
# 使用您希望获取数据的股票代码，例如 '2330'
contract = api.Contracts.Stocks[option]
kbars = api.kbars(contract, start = str(for_caculate), end = str(today))

# 将获取的数据转换为 DataFrame
df_180 = pd.DataFrame({**kbars})
df_180.ts = pd.to_datetime(df_180.ts)
df_180.set_index("ts", inplace=True)

daily_df = df_180.resample('D').agg({
    'Open': 'first',
    'High': 'max',
    'Low': 'min',
    'Close': 'last',
    'Volume': 'sum'}).dropna()

daily_df.reset_index(inplace=True)
daily_df.set_index('ts', inplace=True)

#60筆資料來畫K線圖
daily_df_60 = daily_df.iloc[-60:,:]

# 确保数据的索引为 DatetimeIndex
daily_df_60.index = pd.to_datetime(daily_df_60.index)

fig_price, ax = mpf.plot(
    daily_df_60,
    type='candle', 
    volume=True, 
    style='charles', 
    title='K Line Chart', 
    ylabel='Price', 
    ylabel_lower='Volume',
    returnfig=True  # 返回图形对象
)

# 在 Streamlit 中显示图表
st.pyplot(fig_price)

# 创建K线图（Plotly）
fig_candle = go.Figure(data=[go.Candlestick(
    x=daily_df_60.index,
    open=daily_df_60['Open'],
    high=daily_df_60['High'],
    low=daily_df_60['Low'],
    close=daily_df_60['Close']
)])

# 调整布局和样式
fig_candle.update_layout(
    title='Candlestick Chart (Plotly)',
    xaxis_title='Date',
    yaxis_title='Price',
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
    margin=dict(l=50, r=50, t=80, b=50),
    width=1000,  # 设置图表宽度
    height=600,  # 设置图表高度
    xaxis=dict(
        tickangle=45,
        type='category',  # 将x轴类型设置为category，去除日期
        tickvals=[], 
        ticktext=[d.strftime('%m-%d') for d in daily_df_60.index],  # 设置ticktext为日期格式
    ),
)

# 在 Streamlit 中显示图表
st.plotly_chart(fig_candle)

# 计算成交量颜色
prev_close = daily_df_60['Close'].shift(fill_value=daily_df_60['Close'].iloc[0])
colors = ['red' if close > prev_close[idx] else 'green' if close < prev_close[idx] else 'grey' for idx, close in enumerate(daily_df_60['Close'])]

# 创建成交量柱状图数据
volume_bar = go.Bar(x=daily_df_60.index,
                    y=daily_df_60['Volume'],
                    marker=dict(color=colors),
                    name='Volume')

# 创建成交量柱状图布局
fig_volume = go.Figure(data=volume_bar)
fig_volume.update_layout(
    title='Volume Chart (Plotly)',
    xaxis_title='Date',
    yaxis_title='Volume',
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
    margin=dict(l=50, r=50, t=80, b=50),
    width=1000,  # 设置图表宽度
    height=200,  # 设置图表高度
    xaxis=dict(
        tickangle=45,
        type='category',  # 将x轴类型设置为category，去除日期
        tickvals=[],
        ticktext=[d.strftime('%m-%d') for d in daily_df_60.index],  # 设置ticktext为日期格式
    ),
)

# 在 Streamlit 中显示成交量图表
st.plotly_chart(fig_volume)

# 计算 MACD
def calculate_macd(df, fastperiod=12, slowperiod=26, signalperiod=9):
    macd = ta.trend.MACD(df['Close'], window_slow=slowperiod, window_fast=fastperiod, window_sign=signalperiod)
    df['MACD'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()
    df['MACD_Hist'] = macd.macd_diff()
    return df

# 计算 KD 指标
def calculate_kd(df, fastk_period=9, slowk_period=3, slowd_period=3):
    stoch = ta.momentum.StochasticOscillator(
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        window=fastk_period,
        smooth_window=slowk_period
    )
    df['K'] = stoch.stoch()
    df['D'] = stoch.stoch_signal()
    return df

# 如果daily_df中有数据，才计算MACD指标
if not daily_df.empty:
    tech = calculate_macd(daily_df)[-60:]
    #tech = calculate_kd(daily_df)[-60:]
    # 创建新的日期标签
    labels = []
    previous_month = None
    for date_str in tech.index:
        date = pd.to_datetime(date_str)
        if date.month != previous_month:
            labels.append(date.strftime('%m-%d'))
            previous_month = date.month
        else:
            labels.append(date.strftime('%d'))

    # 绘制MACD指标图表
    fig_macd = go.Figure()

    # 添加MACD和MACD Signal
    fig_macd.add_trace(go.Scatter(x=tech.index, y=tech['MACD'], mode='lines', name='MACD', line=dict(color='blue')))
    fig_macd.add_trace(go.Scatter(x=tech.index, y=tech['MACD_Signal'], mode='lines', name='MACD Signal', line=dict(color='red')))

    # 添加MACD Histogram
    fig_macd.add_trace(go.Bar(x=tech.index, y=tech['MACD_Hist'], name='MACD Histogram', marker=dict(color=['red' if x > 0 else 'green' for x in tech['MACD_Hist']], line=dict(color='grey', width=0.5))))

    # 设置柱状图的 Y 轴范围，使零线在中间，刻度范围包括 MACD 数据的最大最小值
    max_macd = tech[['MACD', 'MACD_Signal', 'MACD_Hist']].max().max()
    min_macd = tech[['MACD', 'MACD_Signal', 'MACD_Hist']].min().min()
    scale = max(abs(max_macd), abs(min_macd), 3)
    
    # 设置布局和样式
    fig_macd.update_layout(
        title='MACD Indicator',
        xaxis=dict(
            tickmode='array',  # 设置为数组模式
            tickvals=tech.index,
            ticktext=labels,
            tickangle=45,  # 旋转45度
        ),
        yaxis=dict(
        title='Value',
        range=[-scale * 1.05, scale * 1.05]  # 设置 Y 轴范围，使零线在中间，刻度范围包括最大最小值
    ),
    height=600,
    showlegend=True,
    )

    # 在 Streamlit 中显示MACD图表
    st.plotly_chart(fig_macd)


    
# st.write()
# https://docs.streamlit.io/develop/api-reference/write-magic/st.write

# -string
# st.write("Hello World.")

# -FP object
# st.write(1234.5678)

# -emoji shortcodes
# st.write('Hello, *World!* :sunglasses:')

# -LaTeX expression
# st.write("$\sqrt{3x-1}+\sqrt[5]{2y^5-4}$")


# -Pandas DataFrame
# st.write("Pandas Dataframe:")

# df = pd.DataFrame({
#     'first column': [1, 2, 3, 4],
#     'second column': [10, 20, 30, 40]
# })

# st.write(df)

# # -multiple arguments
# st.write('1 + 1 = ', 2)
# st.write('Below is a DataFrame:', df, 'Above is a dataframe.')

# -繪製圖表Chart Objects
# import altair as alt

# df = pd.DataFrame(
#     np.random.randn(200, 3),
#     columns=['a', 'b', 'c'])

# c = alt.Chart(df).mark_circle().encode(
#     x='a', y='b', size='c', color='c', tooltip=['a', 'b', 'c'])

# st.write(c)

# st.markdown()

# st.markdown("*Streamlit* is **really** ***cool***.")
# st.markdown('''
#     :red[Streamlit] :orange[can] :green[write] :blue[text] :violet[in]
#     :gray[pretty] :rainbow[colors] and :blue-background[highlight] text.''')
# st.markdown("Here's a bouquet &mdash;\
#             :tulip::cherry_blossom::rose::hibiscus::sunflower::blossom:")

# # 折線圖 st.line_chart()
# chart_data = pd.DataFrame(np.random.randn(20, 3), columns=["a", "b", "c"])

# st.line_chart(chart_data)

#地圖 st.map()
# df = pd.DataFrame(
#     np.random.randn(1000, 2) / [50, 50] + [37.76, -122.4],
#     columns=['lat', 'lon'])
# st.write(df.head(20))

# st.map(df)


# df = pd.DataFrame({
#     "col1": np.random.randn(1000) / 50 + 37.76,
#     "col2": np.random.randn(1000) / 50 + -122.4,
#     "col3": np.random.randn(1000) * 100,
#     "col4": np.random.rand(1000, 4).tolist(),
# })
# st.write(df.head(20))

# st.map(df,
#     latitude='col1',
#     longitude='col2',
#     size='col3',
#     color='col4')


# 按鈕 st.button()
# st.button("Reset", type="primary")
# if st.button("Say hello"):
#     st.write("Why hello there")
# else:
#     st.write("Goodbye")


# if st.button('按我!'):
#     st.text("好乖喔")

# 複選框 st.checkbox()
# if st.checkbox('顯示地圖圖表'):
#     map_data = pd.DataFrame(
#         np.random.randn(100, 2) / [50, 50] + [22.6, 120.4],
#         columns=['lat', 'lon'])
#     st.map(map_data)


# 選擇框 st.selectbox()
# option = st.selectbox(
#     '你喜歡哪種動物？',
#     ['狗', '貓', '魚', '鳥'])
# st.text(f'你的答案：{option}')

# 側邊欄 st.sidebar()
# option = st.sidebar.selectbox(
#     '你喜歡的顏色？',
#     ['紅', '綠', '白', '黑'])
# st.sidebar.text(f'你的答案：{option}')

# option1 = st.sidebar.selectbox(
#     '你喜歡的食物？',
#     ['炸雞', '排骨', '奶茶'])
# st.sidebar.text(f'你的答案：{option1}')



# 列容器 st.columns()
# left_column, right_column = st.columns(2)
# left_column.write("This is left side")
# right_column.write("This is right side")

# col1, col2, col3 = st.columns(3)

# with col1:
#    st.header("A cat")
#    st.image("https://static.streamlit.io/examples/cat.jpg")

# with col2:
#    st.header("A dog")
#    st.image("https://static.streamlit.io/examples/dog.jpg")

# with col3:
#    st.header("An owl")
#    st.image("https://static.streamlit.io/examples/owl.jpg")

# 展開容器 st.expander()
# expander = st.expander("一年級的老師教小朋友認識家禽動物。\
# 老師：「有一種動物兩隻腳，每天早上太陽公公出來時，\
# 牠都會叫你起床，而且叫到你起床為止，是哪一種動物？")
# expander.write("小朋友：「媽媽！」")


#分頁容器 st.tabs()
# tab1, tab2 = st.tabs(["📈 Chart", "🗃 Data"])
# data = np.random.randn(10, 1)

# tab1.subheader("A tab with a chart")
# tab1.line_chart(data)

# tab2.subheader("A tab with the data")
# tab2.write(data)

# 進度條 st.progress()
# bar = st.progress(0)
# for i in range(100):
#     bar.progress(i + 1, f'目前進度 {i+1} %')
#     time.sleep(0.1)

# bar.progress(100, '載入完成！')

# 消息通知 st.toast()
# if st.button('Three cheers'):
#     st.toast('Hip!')
#     time.sleep(.5)
#     st.toast('Hip!')
#     time.sleep(.5)
#     st.toast('Hooray!', icon='🎉')


# 特效 st.balloons() 與 st.snow()

# st.balloons() 
# st.snow()


# 聊天元件 st.chat_message() 與 st.chat_input()
# message = st.chat_message("assistant") 
# message.write("你好！我是 ChatBot 🤖，可以回答各種問題，提供資訊。")
# message.write("有什麼我可以幫助你的嗎？")

# prompt = st.chat_input("Say something")
# if prompt:
#     st.write(f"User has sent the following prompt: {prompt}")

# 表單 st.form()
# with st.form(key='my_form'):
#     form_name = st.text_input(label='姓名', placeholder='請輸入姓名')
#     form_gender = st.selectbox('性別', ['男', '女', '其他'])
#     form_birthday = st.date_input("生日")
#     submit_button = st.form_submit_button(label='Submit')

# if submit_button:
#     st.write(f'hello {form_name}, 性別:{form_gender}, 生日:{form_birthday}')


# for more examples, refer to https://docs.streamlit.io/ or search “streamlit教學” 
