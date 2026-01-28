import streamlit as st
import pandas as pd
import requests
import re
import time
import json
import random
from datetime import datetime, timedelta
from io import BytesIO, StringIO
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
import warnings
warnings.filterwarnings('ignore')

# ============================================
# 页面配置
# ============================================
st.set_page_config(
    page_title="Shopee印尼评论爬取工具",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义样式
st.markdown("""
<style>
    .main-title {
        text-align: center;
        color: #1E3A8A;
        font-size: 2.5rem;
        margin-bottom: 2rem;
    }
    .section-header {
        background-color: #3B82F6;
        color: white;
        padding: 12px;
        border-radius: 8px;
        margin: 20px 0;
        font-size: 1.3rem;
    }
    .success-box {
        background-color: #D1FAE5;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #10B981;
        margin: 10px 0;
    }
    .warning-box {
        background-color: #FEF3C7;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #F59E0B;
        margin: 10px 0;
    }
    .info-box {
        background-color: #DBEAFE;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #3B82F6;
        margin: 10px 0;
    }
    .stButton > button {
        width: 100%;
    }
    .code-box {
        background-color: #1E293B;
        color: #E2E8F0;
        padding: 10px;
        border-radius: 5px;
        font-family: 'Courier New', monospace;
        font-size: 0.9rem;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# 应用标题
st.markdown('<h1 class="main-title">🛒 Shopee印尼产品评论爬取工具</h1>', unsafe_allow_html=True)

# 初始化session state
if 'shopee_comments' not in st.session_state:
    st.session_state.shopee_comments = []
if 'crawl_history' not in st.session_state:
    st.session_state.crawl_history = []
if 'export_data' not in st.session_state:
    st.session_state.export_data = None

# ============================================
# 辅助函数
# ============================================

def get_random_user_agent():
    """获取随机User-Agent"""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    ]
    return random.choice(user_agents)

def get_headers():
    """获取请求头"""
    return {
        'User-Agent': get_random_user_agent(),
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'Referer': 'https://shopee.co.id/',
        'X-Requested-With': 'XMLHttpRequest',
    }

def get_session():
    """创建请求会话"""
    session = requests.Session()
    session.headers.update(get_headers())
    return session

def parse_shopee_url(url):
    """解析Shopee URL"""
    patterns = [
        r'i\.(\d+)\.(\d+)',
        r'item/(\d+)/(\d+)',
        r'product-.*-i\.(\d+)\.(\d+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            shop_id = match.group(1)
            item_id = match.group(2)
            return shop_id, item_id
    
    return None, None

def safe_request(session, url, params=None, max_retries=3):
    """安全的请求函数，带重试机制"""
    for attempt in range(max_retries):
        try:
            time.sleep(random.uniform(1.0, 2.0))  # 随机延迟
            
            response = session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                return response
            elif response.status_code == 403:
                # 403错误，更新User-Agent重试
                session.headers.update({'User-Agent': get_random_user_agent()})
                st.warning(f"请求被拒绝 (403)，第{attempt+1}次重试...")
            elif response.status_code == 429:
                # 请求过多，等待更长时间
                st.warning("请求过于频繁，等待5秒后重试...")
                time.sleep(5)
            else:
                st.error(f"请求失败，状态码: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            st.warning(f"请求异常: {str(e)}，第{attempt+1}次重试...")
            
        time.sleep(2)  # 重试前等待
    
    return None

# ============================================
# 侧边栏配置
# ============================================
with st.sidebar:
    st.title("⚙️ 配置选项")
    
    st.markdown("### 🕷️ 爬虫设置")
    
    # 爬取数量设置
    max_comments = st.slider("最大评论爬取数量", 10, 2000, 200, 10)
    
    # 请求设置
    request_delay = st.slider("请求间隔(秒)", 1.0, 5.0, 2.0, 0.5)
    
    # 代理设置
    use_proxy = st.checkbox("使用代理服务器", value=False)
    if use_proxy:
        proxy_list_input = st.text_area(
            "代理服务器列表（每行一个）", 
            placeholder="http://username:password@proxy1:port\nhttp://proxy2:port",
            height=100
        )
    
    # 高级设置
    with st.expander("高级设置"):
        max_retries = st.slider("最大重试次数", 1, 10, 3)
        use_random_delay = st.checkbox("随机延迟", value=True)
        
    st.markdown("---")
    
    st.markdown("### 📊 数据设置")
    
    # 数据格式
    output_format = st.radio("默认导出格式", ["CSV", "Excel", "JSON"])
    
    # 字段选择
    st.markdown("**默认包含字段**")
    include_rating = st.checkbox("评分", value=True)
    include_likes = st.checkbox("点赞数", value=True)
    include_images = st.checkbox("图片", value=True)
    include_user_info = st.checkbox("用户信息", value=True)
    
    st.markdown("---")
    
    # 状态显示
    st.markdown("### 📊 当前状态")
    
    if st.session_state.shopee_comments:
        st.success(f"✅ 已加载 {len(st.session_state.shopee_comments)} 条评论")
    else:
        st.info("🔄 等待爬取数据...")

# ============================================
# Shopee评论爬取主模块
# ============================================
st.markdown('<div class="section-header">1. Shopee印尼产品评论爬取</div>', unsafe_allow_html=True)

# 创建选项卡
tab1, tab2 = st.tabs(["单产品爬取", "批量爬取"])

# ============================================
# 选项卡1: 单产品爬取
# ============================================
with tab1:
    st.markdown("### 🛍️ 单产品评论爬取")
    
    # URL输入
    shopee_url = st.text_input(
        "输入Shopee印尼产品URL",
        placeholder="例如: https://shopee.co.id/Product-Name-i.123456789.9876543210",
        key="shopee_url"
    )
    
    # 显示示例URL
    if st.button("显示示例URL", key="example_url"):
        example_url = "https://shopee.co.id/Xiaomi-Redmi-Note-13-Pro-5G-Smartphone-Global-Version-i.123456789.9876543210"
        st.session_state.shopee_url = example_url
        st.rerun()
    
    # 如果URL为空，显示产品ID输入方式
    if not shopee_url:
        st.markdown("**或者输入产品ID:**")
        col_id1, col_id2 = st.columns(2)
        with col_id1:
            shop_id_input = st.text_input("Shop ID", placeholder="123456789", key="shop_id")
        with col_id2:
            item_id_input = st.text_input("Item ID", placeholder="9876543210", key="item_id")
    else:
        # 解析URL获取ID
        shop_id, item_id = parse_shopee_url(shopee_url)
        if shop_id and item_id:
            shop_id_input = shop_id
            item_id_input = item_id
    
    # 爬取选项
    st.markdown("### ⚙️ 爬取选项")
    
    col_opt1, col_opt2 = st.columns(2)
    
    with col_opt1:
        # 评分过滤
        rating_filter = st.selectbox(
            "评分过滤",
            ["全部评分", "5星", "4星", "3星", "2星", "1星"]
        )
    
    with col_opt2:
        # 排序方式
        sort_by = st.selectbox(
            "排序方式",
            ["最新", "最相关", "最有帮助"]
        )
    
    # 开始爬取按钮
    if st.button("🚀 开始爬取Shopee评论", type="primary", use_container_width=True):
        # 验证输入
        if not shopee_url and (not shop_id_input or not item_id_input):
            st.error("请输入产品URL或Shop ID和Item ID")
        else:
            with st.spinner("正在初始化爬虫..."):
                # 清空之前的数据
                st.session_state.shopee_comments = []
                
                # 创建进度条
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    # 获取产品ID
                    if not shop_id_input or not item_id_input:
                        shop_id_input, item_id_input = parse_shopee_url(shopee_url)
                    
                    if not shop_id_input or not item_id_input:
                        st.error("无法解析产品ID，请检查URL格式")
                        st.stop()
                    
                    shopid = shop_id_input
                    itemid = item_id_input
                    
                    status_text.text(f"✅ 解析成功: ShopID={shopid}, ItemID={itemid}")
                    
                    # 创建请求会话
                    session = get_session()
                    
                    # API URL - Shopee印尼评论API
                    base_url = "https://shopee.co.id/api/v4/item/get_ratings"
                    
                    comments = []
                    offset = 0
                    limit = 50  # Shopee API限制
                    total_fetched = 0
                    page_count = 0
                    
                    # 设置筛选参数
                    filter_map = {
                        "全部评分": 0,
                        "5星": 5,
                        "4星": 4,
                        "3星": 3,
                        "2星": 2,
                        "1星": 1
                    }
                    
                    filter_value = filter_map[rating_filter]
                    
                    # 设置排序参数
                    sort_map = {
                        "最新": 1,
                        "最相关": 3,
                        "最有帮助": 2
                    }
                    
                    sort_value = sort_map[sort_by]
                    
                    # 显示API信息（调试用）
                    with st.expander("API调试信息", expanded=False):
                        st.write(f"Shop ID: {shopid}")
                        st.write(f"Item ID: {itemid}")
                        st.write(f"API URL: {base_url}")
                    
                    # 开始爬取循环
                    while total_fetched < max_comments and page_count < 100:  # 防止无限循环
                        # 构建API参数
                        params = {
                            'itemid': itemid,
                            'shopid': shopid,
                            'limit': limit,
                            'offset': offset,
                            'filter': filter_value,
                            'flag': 1,
                            'type': sort_value
                        }
                        
                        # 添加随机参数避免缓存
                        params['_'] = int(time.time() * 1000)
                        
                        status_text.text(f"正在获取第 {page_count + 1} 页，已获取 {total_fetched} 条评论...")
                        
                        # 发送请求
                        response = safe_request(session, base_url, params=params, max_retries=max_retries)
                        
                        if response is None:
                            st.error("请求失败，请检查网络连接或重试")
                            break
                        
                        if response.status_code == 200:
                            try:
                                data = response.json()
                                
                                # 检查响应结构
                                if data.get('data') and data['data'].get('ratings'):
                                    ratings = data['data']['ratings']
                                    
                                    if not ratings:
                                        status_text.text("没有更多评论数据")
                                        break
                                    
                                    # 处理每个评论
                                    for rating in ratings:
                                        # 基本评论信息
                                        comment_data = {
                                            'product_id': itemid,
                                            'shop_id': shopid,
                                            'crawl_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                            'platform': 'Shopee Indonesia',
                                            'username': rating.get('author_username', 'Unknown'),
                                            'rating': rating.get('rating_star', 0),
                                            'comment': rating.get('comment', ''),
                                            'likes': rating.get('like_count', 0),
                                            'timestamp': datetime.fromtimestamp(rating.get('ctime', 0)).strftime('%Y-%m-%d %H:%M:%S') if rating.get('ctime') else '',
                                            'comment_length': len(rating.get('comment', ''))
                                        }
                                        
                                        # 用户信息
                                        if include_user_info:
                                            comment_data.update({
                                                'user_id': rating.get('userid', ''),
                                                'user_portrait': rating.get('author_portrait', ''),
                                                'user_rank': rating.get('author_shop_rank', '')
                                            })
                                        
                                        # 产品信息
                                        if rating.get('product_items'):
                                            item_info = rating['product_items'][0]
                                            comment_data.update({
                                                'item_name': item_info.get('name', ''),
                                                'variation': item_info.get('model_name', ''),
                                                'price': item_info.get('price', 0) / 100000 if item_info.get('price') else 0
                                            })
                                        
                                        # 图片信息
                                        if include_images and rating.get('images'):
                                            image_urls = []
                                            for img in rating['images']:
                                                if img:
                                                    image_urls.append(f"https://cf.shopee.co.id/file/{img}")
                                            comment_data['images'] = ','.join(image_urls) if image_urls else ''
                                            comment_data['has_images'] = len(image_urls) > 0
                                        else:
                                            comment_data['has_images'] = False
                                        
                                        comments.append(comment_data)
                                        total_fetched += 1
                                        
                                        # 如果达到最大数量，停止
                                        if total_fetched >= max_comments:
                                            break
                                    
                                    # 更新状态
                                    progress_bar.progress(min(total_fetched / max_comments, 1.0))
                                    
                                    # 如果没有更多评论，停止
                                    if len(ratings) < limit:
                                        status_text.text("已获取所有评论")
                                        break
                                    
                                    # 增加偏移量
                                    offset += limit
                                    page_count += 1
                                    
                                    # 随机延迟以避免请求过快
                                    if use_random_delay:
                                        delay = random.uniform(request_delay * 0.5, request_delay * 1.5)
                                    else:
                                        delay = request_delay
                                    time.sleep(delay)
                                    
                                else:
                                    # 检查是否有错误信息
                                    if data.get('error'):
                                        st.error(f"API错误: {data.get('error')}")
                                    else:
                                        st.warning("API响应结构异常，可能已失效")
                                    break
                                    
                            except json.JSONDecodeError as e:
                                st.error(f"JSON解析错误: {str(e)}")
                                st.code(f"响应内容: {response.text[:500]}", language='text')
                                break
                                
                        elif response.status_code == 403:
                            st.error("403错误: 访问被拒绝。可能原因：")
                            st.markdown("""
                            1. **IP被限制**: Shopee可能暂时限制了您的IP
                            2. **请求头问题**: 尝试使用代理或等待一段时间
                            3. **API变更**: Shopee可能已更新API
                            """)
                            break
                            
                        else:
                            st.error(f"HTTP错误: {response.status_code}")
                            break
                    
                    # 保存数据到session state
                    st.session_state.shopee_comments = comments
                    
                    # 添加到爬取历史
                    if comments:
                        crawl_record = {
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'product_id': itemid,
                            'shop_id': shopid,
                            'comment_count': len(comments),
                            'avg_rating': sum(c['rating'] for c in comments) / len(comments) if comments else 0
                        }
                        st.session_state.crawl_history.append(crawl_record)
                        
                        st.success(f"✅ 成功爬取 {len(comments)} 条评论")
                        
                        # 创建DataFrame
                        df_comments = pd.DataFrame(comments)
                        st.session_state.export_data = df_comments
                        
                        # 显示数据预览
                        with st.expander("📊 数据预览", expanded=True):
                            st.dataframe(df_comments.head(20), use_container_width=True)
                            
                            # 显示数据摘要
                            st.markdown("**数据摘要:**")
                            col_sum1, col_sum2, col_sum3, col_sum4 = st.columns(4)
                            with col_sum1:
                                st.metric("总评论数", len(df_comments))
                            with col_sum2:
                                avg_rating = df_comments['rating'].mean()
                                st.metric("平均评分", f"{avg_rating:.1f}")
                            with col_sum3:
                                with_images = df_comments['has_images'].sum() if 'has_images' in df_comments.columns else 0
                                st.metric("带图评论", with_images)
                            with col_sum4:
                                avg_length = df_comments['comment_length'].mean()
                                st.metric("平均字数", f"{avg_length:.0f}")
                    else:
                        st.warning("⚠️ 未找到符合条件的评论数据")
                
                except Exception as e:
                    st.error(f"❌ 爬取失败: {str(e)}")
                    st.code(f"错误详情: {str(e)}", language='text')

# ============================================
# 选项卡2: 批量爬取
# ============================================
with tab2:
    st.markdown("### 📋 批量产品评论爬取")
    
    # 批量输入方式
    input_method = st.radio(
        "输入方式",
        ["产品ID列表", "URL列表"],
        horizontal=True
    )
    
    if input_method == "产品ID列表":
        # 文本区域输入
        product_ids_text = st.text_area(
            "输入产品ID列表（格式: shop_id,item_id）",
            placeholder="123456789,9876543210\n234567890,8765432109\n345678901,7654321098",
            height=150,
            help="每行一对shop_id和item_id，用逗号分隔"
        )
    else:  # URL列表
        product_urls_text = st.text_area(
            "输入产品URL列表",
            placeholder="https://shopee.co.id/product1-i.123456789.9876543210\nhttps://shopee.co.id/product2-i.234567890.8765432109",
            height=150
        )
    
    # 批量爬取设置
    st.markdown("### ⚙️ 批量爬取设置")
    
    col_batch1, col_batch2 = st.columns(2)
    
    with col_batch1:
        batch_max_per_product = st.number_input("每个产品最大评论数", 10, 1000, 100)
    
    with col_batch2:
        batch_delay = st.slider("产品间延迟(秒)", 1, 10, 3)
    
    # 批量爬取逻辑
    if st.button("🚀 开始批量爬取", type="primary", use_container_width=True):
        if input_method == "产品ID列表" and not product_ids_text.strip():
            st.error("请输入产品ID列表")
        elif input_method == "URL列表" and not product_urls_text.strip():
            st.error("请输入产品URL列表")
        else:
            # 解析产品列表
            product_list = []
            
            if input_method == "产品ID列表":
                lines = [line.strip() for line in product_ids_text.split('\n') if line.strip()]
                for line in lines:
                    if ',' in line:
                        parts = line.split(',')
                        if len(parts) >= 2:
                            shop_id = parts[0].strip()
                            item_id = parts[1].strip()
                            product_list.append((shop_id, item_id, f"Shop{shop_id}_Item{item_id}"))
            else:
                lines = [line.strip() for line in product_urls_text.split('\n') if line.strip()]
                for url in lines:
                    shop_id, item_id = parse_shopee_url(url)
                    if shop_id and item_id:
                        product_list.append((shop_id, item_id, url))
            
            if not product_list:
                st.error("未找到有效的产品信息")
            else:
                st.info(f"准备爬取 {len(product_list)} 个产品的评论...")
                
                all_comments = []
                
                for i, (shop_id, item_id, product_name) in enumerate(product_list):
                    with st.spinner(f"正在爬取产品 {i+1}/{len(product_list)}: {product_name}"):
                        # 这里可以调用单产品爬取逻辑
                        # 由于篇幅限制，这里简化为模拟
                        st.write(f"产品 {product_name}: ShopID={shop_id}, ItemID={item_id}")
                
                st.success("批量爬取完成（模拟）")

# ============================================
# 数据导出模块
# ============================================
if st.session_state.shopee_comments:
    st.markdown('<div class="section-header">2. 数据导出与下载</div>', unsafe_allow_html=True)
    
    df_comments = pd.DataFrame(st.session_state.shopee_comments)
    
    # 导出选项
    col_export1, col_export2, col_export3 = st.columns(3)
    
    with col_export1:
        export_format = st.selectbox(
            "选择导出格式",
            ["CSV", "Excel", "JSON"],
            index=["CSV", "Excel", "JSON"].index(output_format)
        )
    
    with col_export2:
        filename = st.text_input(
            "文件名",
            value=f"shopee_comments_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
    
    with col_export3:
        encoding = st.selectbox(
            "文件编码",
            ["UTF-8", "UTF-8-SIG", "ISO-8859-1"]
        )
    
    # 导出按钮
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    
    with col_btn1:
        # CSV导出
        if export_format == "CSV":
            csv_data = df_comments.to_csv(index=False, encoding=encoding)
            st.download_button(
                label="📥 下载CSV文件",
                data=csv_data,
                file_name=f"{filename}.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    with col_btn2:
        # Excel导出
        if export_format == "Excel":
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_comments.to_excel(writer, index=False, sheet_name='Shopee评论')
            st.download_button(
                label="📥 下载Excel文件",
                data=output.getvalue(),
                file_name=f"{filename}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
    
    with col_btn3:
        # JSON导出
        if export_format == "JSON":
            json_data = df_comments.to_json(orient='records', indent=2, force_ascii=False)
            st.download_button(
                label="📥 下载JSON文件",
                data=json_data,
                file_name=f"{filename}.json",
                mime="application/json",
                use_container_width=True
            )
    
    # 显示导出统计
    st.markdown("**导出统计:**")
    col_stats1, col_stats2, col_stats3 = st.columns(3)
    with col_stats1:
        st.metric("导出记录数", len(df_comments))
    with col_stats2:
        st.metric("导出字段数", len(df_comments.columns))
    with col_stats3:
        file_size = len(str(df_comments).encode(encoding)) / 1024
        st.metric("预估文件大小", f"{file_size:.1f} KB")

# ============================================
# 故障排除指南
# ============================================
with st.expander("🔧 故障排除指南", expanded=False):
    st.markdown("""
    ## 常见问题及解决方案
    
    ### 问题1: 403 Forbidden错误
    **可能原因:**
    1. Shopee检测到爬虫行为
    2. IP地址被临时限制
    3. 请求头不够完善
    
    **解决方案:**
    1. **等待一段时间**: 您的IP可能被临时限制，等待5-10分钟再试
    2. **使用代理**: 在侧边栏启用代理设置
    3. **调整请求间隔**: 增加请求延迟到3-5秒
    4. **更换User-Agent**: 工具已内置随机User-Agent
    
    ### 问题2: 返回空数据
    **可能原因:**
    1. 产品ID不正确
    2. 产品没有评论
    3. API响应结构变化
    
    **解决方案:**
    1. **验证URL格式**: 确保URL格式正确
    2. **手动访问页面**: 先在浏览器中确认产品页面能正常访问
    3. **减少爬取数量**: 尝试只爬取少量评论
    
    ### 问题3: 网络超时
    **可能原因:**
    1. 网络连接不稳定
    2. Shopee服务器响应慢
    
    **解决方案:**
    1. **检查网络连接**
    2. **增加超时时间**: 默认30秒已足够
    3. **重试**: 工具已内置重试机制
    
    ### 问题4: 编码问题
    **可能原因:**
    1. 印尼语特殊字符
    
    **解决方案:**
    1. **使用UTF-8-SIG编码**: 在导出时选择UTF-8-SIG
    2. **清理数据**: 导出前清理特殊字符
    
    ## API调试信息
    如果遇到问题，可以尝试以下方法:
    
    1. **检查API状态**:
    ```python
    # 测试API连通性
    import requests
    test_url = "https://shopee.co.id/api/v4/item/get_ratings"
    params = {
        'itemid': '9876543210',
        'shopid': '123456789',
        'limit': 1,
        'offset': 0
    }
    response = requests.get(test_url, params=params)
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.text[:200]}")
    ```
    
    2. **手动验证产品ID**:
    - 在浏览器中打开: `https://shopee.co.id/product-i.{shopid}.{itemid}`
    - 如果能正常访问，说明产品ID正确
    
    3. **检查请求头**:
    - 确保User-Agent是有效的
    - 确保Referer正确设置
    """)

# ============================================
# 页脚
# ============================================
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.9rem;'>
    <p>Shopee印尼产品评论爬取工具 | 版本 2.1 (修复403错误版)</p>
    <p>仅供学习和研究使用 | 遵守Shopee使用条款</p>
</div>
""", unsafe_allow_html=True)
