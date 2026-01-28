import streamlit as st
import pandas as pd
import requests
import re
import time
import json
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
    .metric-card {
        background-color: #F8FAFC;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #E2E8F0;
        text-align: center;
        margin: 5px;
    }
    .stButton > button {
        width: 100%;
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
# 侧边栏配置
# ============================================
with st.sidebar:
    st.title("⚙️ 配置选项")
    
    st.markdown("### 🕷️ 爬虫设置")
    
    # 爬取数量设置
    max_comments = st.slider("最大评论爬取数量", 10, 5000, 500, 10)
    
    # 请求设置
    request_delay = st.slider("请求间隔(秒)", 0.5, 5.0, 1.0, 0.5)
    
    # 代理设置
    use_proxy = st.checkbox("使用代理服务器", value=False)
    if use_proxy:
        proxy_list_input = st.text_area("代理服务器列表（每行一个）", 
                                      placeholder="http://username:password@proxy1:port\nhttp://proxy2:port",
                                      height=100)
    
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
    
    st.markdown("### 📈 分析设置")
    
    # 分析选项
    auto_analyze = st.checkbox("自动分析数据", value=True)
    generate_charts = st.checkbox("生成可视化图表", value=True)
    
    st.markdown("---")
    
    st.markdown("### 📚 使用说明")
    
    with st.expander("点击查看详细说明"):
        st.markdown("""
        **URL格式示例:**
        ```
        https://shopee.co.id/product-name-i.123456789.9876543210
        ```
        
        **产品ID格式:**
        ```
        Shop ID: 123456789
        Item ID: 9876543210
        ```
        
        **功能说明:**
        1. 支持单个产品评论爬取
        2. 支持批量产品评论爬取
        3. 支持评论筛选和排序
        4. 数据分析和可视化
        5. 多种格式导出
        
        **注意事项:**
        - 请合理设置爬取频率
        - 遵守Shopee使用条款
        - 仅用于学习和研究
        """)
    
    # 状态显示
    st.markdown("---")
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
tab1, tab2, tab3 = st.tabs(["单产品爬取", "批量爬取", "URL列表爬取"])

# ============================================
# 选项卡1: 单产品爬取
# ============================================
with tab1:
    st.markdown("### 🛍️ 单产品评论爬取")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # URL输入
        shopee_url = st.text_input(
            "输入Shopee印尼产品URL",
            placeholder="例如: https://shopee.co.id/Product-Name-i.123456789.9876543210",
            key="shopee_url"
        )
    
    with col2:
        # 输入示例按钮
        if st.button("显示示例URL", use_container_width=True):
            st.session_state.shopee_url = "https://shopee.co.id/Xiaomi-Redmi-Note-13-Pro-5G-Smartphone-Global-Version-i.123456789.9876543210"
            st.rerun()
    
    # 如果URL为空，显示产品ID输入方式
    if not shopee_url:
        st.markdown("**或者输入产品ID:**")
        col_id1, col_id2 = st.columns(2)
        with col_id1:
            shop_id_input = st.text_input("Shop ID", placeholder="123456789")
        with col_id2:
            item_id_input = st.text_input("Item ID", placeholder="9876543210")
    
    # 爬取选项
    st.markdown("### ⚙️ 爬取选项")
    
    col_opt1, col_opt2, col_opt3 = st.columns(3)
    
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
    
    with col_opt3:
        # 评论类型
        comment_type = st.selectbox(
            "评论类型",
            ["全部评论", "仅文字评论", "仅图片评论", "视频评论"]
        )
    
    # 高级选项
    with st.expander("高级选项"):
        col_adv1, col_adv2 = st.columns(2)
        
        with col_adv1:
            # 时间范围
            time_range = st.selectbox(
                "时间范围",
                ["全部时间", "最近7天", "最近30天", "最近90天", "最近1年"]
            )
            
            # 语言筛选
            language_filter = st.selectbox(
                "语言筛选",
                ["全部语言", "印尼语", "英语", "中文"]
            )
        
        with col_adv2:
            # 最小字数
            min_words = st.number_input("最小评论字数", 0, 500, 0)
            
            # 最大字数
            max_words = st.number_input("最大评论字数", 0, 500, 500)
    
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
                    # 提取或设置产品ID
                    if shopee_url:
                        # 从URL提取shopid和itemid
                        id_match = re.search(r'i\.(\d+)\.(\d+)', shopee_url)
                        if id_match:
                            shopid = id_match.group(1)
                            itemid = id_match.group(2)
                            status_text.text(f"✅ 解析成功: ShopID={shopid}, ItemID={itemid}")
                        else:
                            st.error("无法从URL解析产品ID")
                            st.stop()
                    else:
                        shopid = shop_id_input
                        itemid = item_id_input
                    
                    # 设置API参数
                    base_url = "https://shopee.co.id/api/v2/item/get_ratings"
                    
                    comments = []
                    offset = 0
                    limit = 50
                    total_fetched = 0
                    
                    # 设置请求头
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Accept': 'application/json',
                        'Accept-Language': 'id-ID,id;q=0.9,en;q=0.8',
                        'Referer': f'https://shopee.co.id/product-i.{shopid}.{itemid}',
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                    
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
                    
                    # 开始爬取循环
                    while total_fetched < max_comments:
                        # 构建API参数
                        params = {
                            'itemid': itemid,
                            'shopid': shopid,
                            'limit': limit,
                            'offset': offset,
                            'filter': filter_value,
                            'flag': 1,
                            'type': 0
                        }
                        
                        # 发送请求
                        try:
                            response = requests.get(base_url, params=params, headers=headers, timeout=30)
                            
                            if response.status_code == 200:
                                data = response.json()
                                
                                if data.get('data') and data['data'].get('ratings'):
                                    ratings = data['data']['ratings']
                                    
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
                                            'timestamp': datetime.fromtimestamp(rating.get('ctime', 0)).strftime('%Y-%m-%d %H:%M:%S'),
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
                                        
                                        # 视频信息
                                        if rating.get('video_upload_time'):
                                            comment_data['has_video'] = True
                                            comment_data['video_url'] = rating.get('video_url', '')
                                        else:
                                            comment_data['has_video'] = False
                                        
                                        # 追加条件筛选
                                        should_include = True
                                        
                                        # 评论类型筛选
                                        if comment_type == "仅文字评论" and comment_data.get('has_images'):
                                            should_include = False
                                        elif comment_type == "仅图片评论" and not comment_data.get('has_images'):
                                            should_include = False
                                        elif comment_type == "视频评论" and not comment_data.get('has_video'):
                                            should_include = False
                                        
                                        # 字数筛选
                                        if min_words > 0 and len(comment_data['comment']) < min_words:
                                            should_include = False
                                        if max_words > 0 and len(comment_data['comment']) > max_words:
                                            should_include = False
                                        
                                        if should_include:
                                            comments.append(comment_data)
                                            total_fetched += 1
                                    
                                    # 更新状态
                                    status_text.text(f"已爬取 {total_fetched}/{max_comments} 条评论...")
                                    progress_bar.progress(min(total_fetched / max_comments, 1.0))
                                    
                                    # 如果没有更多评论或达到限制，停止
                                    if len(ratings) < limit or total_fetched >= max_comments:
                                        break
                                    
                                    # 增加偏移量
                                    offset += limit
                                    
                                    # 延迟以避免请求过快
                                    time.sleep(request_delay)
                                
                                else:
                                    status_text.text("未找到更多评论数据")
                                    break
                            else:
                                st.error(f"API请求失败: {response.status_code}")
                                break
                        
                        except requests.exceptions.RequestException as e:
                            st.error(f"请求异常: {str(e)}")
                            break
                    
                    # 保存数据到session state
                    st.session_state.shopee_comments = comments
                    
                    # 添加到爬取历史
                    crawl_record = {
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'product_id': itemid,
                        'shop_id': shopid,
                        'comment_count': len(comments),
                        'avg_rating': sum(c['rating'] for c in comments) / len(comments) if comments else 0
                    }
                    st.session_state.crawl_history.append(crawl_record)
                    
                    # 显示结果
                    if comments:
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
                    st.code(f"错误详情: {str(e)}")

# ============================================
# 选项卡2: 批量爬取
# ============================================
with tab2:
    st.markdown("### 📋 批量产品评论爬取")
    
    # 批量输入方式
    input_method = st.radio(
        "输入方式",
        ["产品ID列表", "CSV文件上传"],
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
        
        # 示例数据按钮
        if st.button("加载示例数据", key="example_batch"):
            product_ids_text = "123456789,9876543210\n234567890,8765432109\n345678901,7654321098"
            st.rerun()
    
    else:  # CSV文件上传
        uploaded_file = st.file_uploader(
            "上传CSV文件",
            type=['csv'],
            help="CSV文件应包含shop_id和item_id两列"
        )
        
        if uploaded_file:
            try:
                df_uploaded = pd.read_csv(uploaded_file)
                if 'shop_id' in df_uploaded.columns and 'item_id' in df_uploaded.columns:
                    product_pairs = list(zip(df_uploaded['shop_id'], df_uploaded['item_id']))
                    product_ids_text = '\n'.join([f"{shop},{item}" for shop, item in product_pairs])
                    st.success(f"成功读取 {len(product_pairs)} 个产品")
                else:
                    st.error("CSV文件必须包含'shop_id'和'item_id'列")
            except Exception as e:
                st.error(f"读取CSV文件失败: {str(e)}")
    
    # 批量爬取设置
    st.markdown("### ⚙️ 批量爬取设置")
    
    col_batch1, col_batch2 = st.columns(2)
    
    with col_batch1:
        batch_max_per_product = st.number_input("每个产品最大评论数", 10, 1000, 100)
    
    with col_batch2:
        batch_concurrent = st.slider("并发爬取数量", 1, 10, 3)
    
    # 开始批量爬取按钮
    if st.button("🚀 开始批量爬取", type="primary", use_container_width=True):
        if not product_ids_text.strip():
            st.error("请输入产品ID列表")
        else:
            # 解析产品ID
            product_lines = [line.strip() for line in product_ids_text.split('\n') if line.strip()]
            product_pairs = []
            
            for line in product_lines:
                if ',' in line:
                    parts = line.split(',')
                    if len(parts) >= 2:
                        shop_id = parts[0].strip()
                        item_id = parts[1].strip()
                        product_pairs.append((shop_id, item_id))
            
            if not product_pairs:
                st.error("未找到有效的产品ID对")
            else:
                st.info(f"准备爬取 {len(product_pairs)} 个产品的评论...")
                
                # 这里可以添加批量爬取逻辑
                # 注意：在Streamlit Cloud环境中，建议使用顺序爬取而非并发
                st.warning("批量爬取功能在Streamlit Cloud环境中有限制。建议使用单个产品爬取功能，或分批次处理。")

# ============================================
# 选项卡3: URL列表爬取
# ============================================
with tab3:
    st.markdown("### 🔗 URL列表爬取")
    
    # URL列表输入
    url_list_text = st.text_area(
        "输入Shopee产品URL列表",
        placeholder="https://shopee.co.id/product1-i.123456789.9876543210\nhttps://shopee.co.id/product2-i.234567890.8765432109",
        height=150
    )
    
    # URL解析和验证
    if url_list_text:
        urls = [url.strip() for url in url_list_text.split('\n') if url.strip()]
        valid_urls = []
        url_products = []
        
        for url in urls:
            match = re.search(r'i\.(\d+)\.(\d+)', url)
            if match:
                shop_id = match.group(1)
                item_id = match.group(2)
                valid_urls.append(url)
                url_products.append((shop_id, item_id))
        
        if valid_urls:
            st.success(f"✅ 找到 {len(valid_urls)} 个有效URL")
            
            # 显示解析结果
            with st.expander("查看解析结果"):
                for i, (url, (shop_id, item_id)) in enumerate(zip(valid_urls, url_products)):
                    st.write(f"{i+1}. {url}")
                    st.write(f"   Shop ID: {shop_id}, Item ID: {item_id}")
    
    # URL爬取选项
    if st.button("🚀 开始URL列表爬取", type="primary", use_container_width=True):
        st.info("此功能实现方式与批量爬取类似，需要逐个处理URL")

# ============================================
# 数据分析模块
# ============================================
if st.session_state.shopee_comments:
    st.markdown('<div class="section-header">2. 数据分析与可视化</div>', unsafe_allow_html=True)
    
    df_comments = pd.DataFrame(st.session_state.shopee_comments)
    
    # 创建数据分析选项卡
    analysis_tabs = st.tabs(["评分分析", "评论分析", "时间分析", "用户分析"])
    
    with analysis_tabs[0]:
        st.markdown("### ⭐ 评分分布分析")
        
        if 'rating' in df_comments.columns:
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                # 评分分布柱状图
                rating_counts = df_comments['rating'].value_counts().sort_index()
                fig1, ax1 = plt.subplots(figsize=(8, 5))
                bars = ax1.bar(rating_counts.index.astype(str) + '星', rating_counts.values, color=['#EF4444', '#F97316', '#FBBF24', '#10B981', '#3B82F6'])
                ax1.set_xlabel('评分')
                ax1.set_ylabel('评论数量')
                ax1.set_title('评分分布')
                
                # 在柱子上显示数量
                for bar in bars:
                    height = bar.get_height()
                    ax1.text(bar.get_x() + bar.get_width()/2., height,
                            f'{int(height)}', ha='center', va='bottom')
                
                st.pyplot(fig1)
                plt.close(fig1)
            
            with col_chart2:
                # 评分百分比饼图
                fig2, ax2 = plt.subplots(figsize=(8, 5))
                colors = ['#EF4444', '#F97316', '#FBBF24', '#10B981', '#3B82F6']
                wedges, texts, autotexts = ax2.pie(rating_counts.values, labels=rating_counts.index.astype(str) + '星', 
                                                  autopct='%1.1f%%', colors=colors, startangle=90)
                ax2.set_title('评分百分比分布')
                st.pyplot(fig2)
                plt.close(fig2)
            
            # 评分统计
            st.markdown("**评分统计:**")
            col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
            with col_stat1:
                st.metric("平均评分", f"{df_comments['rating'].mean():.2f}")
            with col_stat2:
                st.metric("评分中位数", f"{df_comments['rating'].median():.0f}")
            with col_stat3:
                st.metric("评分标准差", f"{df_comments['rating'].std():.2f}")
            with col_stat4:
                st.metric("评分范围", f"{df_comments['rating'].min()} - {df_comments['rating'].max()}")
    
    with analysis_tabs[1]:
        st.markdown("### 💬 评论内容分析")
        
        if 'comment' in df_comments.columns:
            # 评论长度分析
            if 'comment_length' in df_comments.columns:
                col_len1, col_len2 = st.columns(2)
                
                with col_len1:
                    # 评论长度分布
                    fig3, ax3 = plt.subplots(figsize=(8, 5))
                    ax3.hist(df_comments['comment_length'], bins=20, edgecolor='black', alpha=0.7, color='#3B82F6')
                    ax3.set_xlabel('评论长度（字符数）')
                    ax3.set_ylabel('评论数量')
                    ax3.set_title('评论长度分布')
                    st.pyplot(fig3)
                    plt.close(fig3)
                
                with col_len2:
                    # 评论长度统计
                    st.markdown("**评论长度统计:**")
                    st.metric("平均长度", f"{df_comments['comment_length'].mean():.1f}")
                    st.metric("中位数长度", f"{df_comments['comment_length'].median():.0f}")
                    st.metric("最短评论", f"{df_comments['comment_length'].min():.0f}")
                    st.metric("最长评论", f"{df_comments['comment_length'].max():.0f}")
            
            # 关键词分析
            st.markdown("#### 🔍 热门关键词")
            
            # 提取所有评论文本
            all_comments = ' '.join(df_comments['comment'].dropna().astype(str).tolist())
            
            # 简单的关键词提取（移除常见停用词）
            import re
            from collections import Counter
            
            # 印尼语常见停用词
            stopwords_id = ['yang', 'dan', 'di', 'dengan', 'ini', 'itu', 'untuk', 'pada', 'ke', 'dari', 
                           'dalam', 'tidak', 'ada', 'sangat', 'bagus', 'baik', 'produk', 'barang']
            
            # 提取单词
            words = re.findall(r'\b\w{3,}\b', all_comments.lower())
            filtered_words = [word for word in words if word not in stopwords_id]
            word_counts = Counter(filtered_words).most_common(20)
            
            # 显示热门关键词
            if word_counts:
                col_key1, col_key2 = st.columns(2)
                
                with col_key1:
                    st.markdown("**最常用词汇:**")
                    for word, count in word_counts[:10]:
                        st.write(f"**{word}**: {count}次")
                
                with col_key2:
                    # 关键词云图（使用条形图模拟）
                    fig4, ax4 = plt.subplots(figsize=(8, 5))
                    top_words = word_counts[:10]
                    words = [w[0] for w in top_words]
                    counts = [w[1] for w in top_words]
                    
                    y_pos = range(len(words))
                    ax4.barh(y_pos, counts, color='#3B82F6')
                    ax4.set_yticks(y_pos)
                    ax4.set_yticklabels(words)
                    ax4.invert_yaxis()
                    ax4.set_xlabel('出现次数')
                    ax4.set_title('热门关键词')
                    
                    st.pyplot(fig4)
                    plt.close(fig4)
    
    with analysis_tabs[2]:
        st.markdown("### 📅 时间趋势分析")
        
        if 'timestamp' in df_comments.columns:
            try:
                # 转换时间戳
                df_comments['timestamp_dt'] = pd.to_datetime(df_comments['timestamp'])
                df_comments['date'] = df_comments['timestamp_dt'].dt.date
                df_comments['hour'] = df_comments['timestamp_dt'].dt.hour
                
                # 按日期统计
                daily_counts = df_comments.groupby('date').size().reset_index(name='count')
                daily_counts = daily_counts.sort_values('date')
                
                # 时间趋势图
                fig5, ax5 = plt.subplots(figsize=(10, 5))
                ax5.plot(daily_counts['date'], daily_counts['count'], marker='o', color='#3B82F6', linewidth=2)
                ax5.set_xlabel('日期')
                ax5.set_ylabel('评论数量')
                ax5.set_title('评论时间趋势')
                ax5.tick_params(axis='x', rotation=45)
                ax5.grid(True, alpha=0.3)
                
                st.pyplot(fig5)
                plt.close(fig5)
                
                # 按小时统计
                hourly_counts = df_comments['hour'].value_counts().sort_index()
                
                fig6, ax6 = plt.subplots(figsize=(10, 5))
                ax6.bar(hourly_counts.index.astype(str), hourly_counts.values, color='#10B981')
                ax6.set_xlabel('小时 (24小时制)')
                ax6.set_ylabel('评论数量')
                ax6.set_title('评论发布时段分布')
                ax6.grid(True, alpha=0.3)
                
                st.pyplot(fig6)
                plt.close(fig6)
                
            except Exception as e:
                st.warning(f"时间分析时出错: {str(e)}")
    
    with analysis_tabs[3]:
        st.markdown("### 👤 用户行为分析")
        
        if 'username' in df_comments.columns:
            # 活跃用户分析
            user_counts = df_comments['username'].value_counts().head(10)
            
            col_user1, col_user2 = st.columns(2)
            
            with col_user1:
                st.markdown("**最活跃用户:**")
                for i, (user, count) in enumerate(user_counts.items(), 1):
                    st.write(f"{i}. **{user}**: {count}条评论")
            
            with col_user2:
                # 用户评论数量分布
                fig7, ax7 = plt.subplots(figsize=(8, 5))
                users = [str(i) for i in range(len(user_counts))]
                ax7.bar(users, user_counts.values, color='#8B5CF6')
                ax7.set_xlabel('用户排名')
                ax7.set_ylabel('评论数量')
                ax7.set_title('活跃用户评论数量分布')
                
                st.pyplot(fig7)
                plt.close(fig7)
            
            # 用户评分分析
            if 'rating' in df_comments.columns:
                user_avg_rating = df_comments.groupby('username')['rating'].mean().sort_values(ascending=False).head(10)
                
                st.markdown("**用户平均评分排名:**")
                for i, (user, rating) in enumerate(user_avg_rating.items(), 1):
                    st.write(f"{i}. **{user}**: {rating:.2f} ⭐")

# ============================================
# 数据导出模块
# ============================================
if st.session_state.shopee_comments:
    st.markdown('<div class="section-header">3. 数据导出与下载</div>', unsafe_allow_html=True)
    
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
    
    # 字段选择
    with st.expander("字段选择"):
        all_columns = list(df_comments.columns)
        default_selected = [col for col in all_columns if col not in ['timestamp_dt', 'date', 'hour']]
        selected_columns = st.multiselect(
            "选择要导出的字段",
            all_columns,
            default=default_selected
        )
    
    # 数据处理选项
    with st.expander("数据处理选项"):
        col_proc1, col_proc2 = st.columns(2)
        
        with col_proc1:
            remove_duplicates = st.checkbox("删除重复评论", value=True)
            sort_by = st.selectbox(
                "排序方式",
                ["按时间倒序", "按评分", "按点赞数", "按评论长度"]
            )
        
        with col_proc2:
            clean_text = st.checkbox("清理评论文本", value=True)
            include_index = st.checkbox("包含索引列", value=False)
    
    # 准备数据
    df_export = df_comments.copy()
    
    if selected_columns:
        df_export = df_export[selected_columns]
    
    if remove_duplicates and 'comment' in df_export.columns:
        df_export = df_export.drop_duplicates(subset=['comment'], keep='first')
    
    # 排序
    if sort_by == "按时间倒序" and 'timestamp' in df_export.columns:
        df_export = df_export.sort_values('timestamp', ascending=False)
    elif sort_by == "按评分" and 'rating' in df_export.columns:
        df_export = df_export.sort_values('rating', ascending=False)
    elif sort_by == "按点赞数" and 'likes' in df_export.columns:
        df_export = df_export.sort_values('likes', ascending=False)
    elif sort_by == "按评论长度" and 'comment_length' in df_export.columns:
        df_export = df_export.sort_values('comment_length', ascending=False)
    
    # 清理文本
    if clean_text and 'comment' in df_export.columns:
        df_export['comment'] = df_export['comment'].str.replace('\r\n', ' ').str.replace('\n', ' ').str.strip()
    
    # 导出按钮
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    
    with col_btn1:
        # CSV导出
        if export_format == "CSV":
            csv_data = df_export.to_csv(index=include_index, encoding=encoding)
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
                df_export.to_excel(writer, index=include_index, sheet_name='Shopee评论')
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
            json_data = df_export.to_json(orient='records', indent=2, force_ascii=False)
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
        st.metric("导出记录数", len(df_export))
    with col_stats2:
        st.metric("导出字段数", len(df_export.columns))
    with col_stats3:
        file_size = len(str(df_export).encode(encoding)) / 1024
        st.metric("预估文件大小", f"{file_size:.1f} KB")

# ============================================
# 爬取历史记录
# ============================================
if st.session_state.crawl_history:
    st.markdown('<div class="section-header">📋 爬取历史记录</div>', unsafe_allow_html=True)
    
    df_history = pd.DataFrame(st.session_state.crawl_history)
    
    # 显示历史记录
    with st.expander("查看爬取历史"):
        st.dataframe(df_history, use_container_width=True)
        
        # 历史统计
        col_hist1, col_hist2, col_hist3 = st.columns(3)
        with col_hist1:
            total_comments = sum(h['comment_count'] for h in st.session_state.crawl_history)
            st.metric("历史总评论数", total_comments)
        with col_hist2:
            st.metric("爬取次数", len(st.session_state.crawl_history))
        with col_hist3:
            if len(st.session_state.crawl_history) > 1:
                first_crawl = pd.to_datetime(st.session_state.crawl_history[0]['timestamp'])
                last_crawl = pd.to_datetime(st.session_state.crawl_history[-1]['timestamp'])
                days_diff = (last_crawl - first_crawl).days
                st.metric("爬取时间跨度", f"{days_diff}天")

# ============================================
# 使用说明
# ============================================
with st.expander("📚 详细使用说明", expanded=False):
    st.markdown("""
    ## 🚀 快速开始指南
    
    ### 1. 单产品评论爬取
    1. 在"单产品爬取"标签页输入Shopee产品URL
    2. 设置爬取选项（评分过滤、排序方式等）
    3. 点击"开始爬取Shopee评论"按钮
    4. 等待爬取完成，查看数据和分析结果
    5. 在"数据导出与下载"部分导出数据
    
    ### 2. 批量爬取
    - **产品ID列表**: 每行输入一对shop_id和item_id
    - **CSV文件上传**: 上传包含shop_id和item_id列的CSV文件
    
    ### 3. URL列表爬取
    直接输入多个Shopee产品URL，每行一个
    
    ## ⚙️ 配置说明
    
    ### 爬虫设置
    - **最大评论爬取数量**: 控制每次爬取的评论数量
    - **请求间隔**: 每次API请求的间隔时间，避免请求过快
    - **代理服务器**: 如果需要，可以配置代理服务器
    
    ### 数据设置
    - **导出格式**: 选择CSV、Excel或JSON格式
    - **包含字段**: 选择需要导出的字段
    
    ## 📊 数据分析功能
    
    工具提供以下分析功能：
    1. **评分分析**: 评分分布、平均评分等
    2. **评论分析**: 评论长度、热门关键词等
    3. **时间分析**: 评论时间趋势、发布时段等
    4. **用户分析**: 活跃用户、用户评分等
    
    ## ⚠️ 注意事项
    
    1. **遵守规则**: 请遵守Shopee的使用条款和robots.txt
    2. **请求频率**: 合理设置请求间隔，避免对Shopee服务器造成压力
    3. **数据用途**: 仅用于学习和研究目的
    4. **网络环境**: 确保网络连接稳定
    
    ## 🔧 故障排除
    
    **问题1: 爬取失败或返回空数据**
    - 检查URL格式是否正确
    - 验证网络连接
    - 尝试调整请求间隔
    
    **问题2: 导出文件乱码**
    - 尝试更改文件编码为UTF-8-SIG
    - 确保文本清理选项已启用
    
    **问题3: 数据分析图表不显示**
    - 检查是否有足够的数据
    - 确保相关字段存在
    """)

# ============================================
# 页脚
# ============================================
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.9rem;'>
    <p>Shopee印尼产品评论爬取工具 | 版本 2.0</p>
    <p>仅供学习和研究使用 | 遵守Shopee使用条款</p>
</div>
""", unsafe_allow_html=True)
