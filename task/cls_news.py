import akshare as ak
import pandas as pd
from datetime import datetime
import os
import uuid
from core.utils.config_setting import Config
from core.llms.llm_factory import LLMFactory
from core.llms.mini_max_pro import MiniMaxProClient
from core.llms.fallback_client import FallbackLLMClient
def runner():
    cls_telegraph_news = ak.stock_info_global_cls()

    # 将发布日期和发布时间组合成新的列日期
    cls_telegraph_news["日期"] = cls_telegraph_news.apply(
        lambda row: datetime.combine(row["发布日期"], row["发布时间"]), axis=1
    )

    # 获取起始时间和结束时间
    start_time = cls_telegraph_news["日期"].min()
    end_time = cls_telegraph_news["日期"].max()

    # 调整起始时间和结束时间
    if start_time.minute < 30:
        start_time = start_time.replace(minute=0, second=0, microsecond=0)
    else:
        start_time = start_time.replace(minute=0, second=0, microsecond=0) + pd.Timedelta(hours=1)

    if end_time.minute < 30:
        end_time = end_time.replace(minute=0, second=0, microsecond=0)
    else:
        end_time = end_time.replace(minute=0, second=0, microsecond=0) + pd.Timedelta(hours=1)

    # 生成time_span字符串
    time_span = f"资讯时间从{start_time.strftime('%Y年%m月%d日%H点')}，到{end_time.strftime('%Y年%m月%d日%H点')}"

    llm_factory = LLMFactory()

    # 确保output文件夹存在
    os.makedirs("output", exist_ok=True)
    
    # 确保 markdown/news/ 目录存在
    os.makedirs("markdown/news", exist_ok=True)

    # 访问之前步骤的数据
    data = cls_telegraph_news
    df = data

    # 使用LLM API进行新闻分析
    reporter = llm_factory.get_reporter("FallbackLLMClient")
    llm_client = llm_factory.get_reporter("FallbackLLMClient")
    
    if isinstance(llm_client, MiniMaxProClient):
        llm_client.debug=True
    if isinstance(reporter, MiniMaxProClient):
        reporter.debug=True

    news_batches = []
    current_batch = ""
    for _, row in data.iterrows():
        news = f"标题: {row['标题']}\n内容: {row['内容']}\n"
        if len(current_batch) + len(news) > 9500:
            news_batches.append(current_batch)
            current_batch = news
        else:
            current_batch += news
    if current_batch:
        news_batches.append(current_batch)

    analysis_results = []
    for batch in news_batches:
        prompt = f"""分析以下新闻，重点关注：
        1. 总结和提炼对市场影响比较大的内容
        2. 金融市场动态总结
        3. 市场情绪的走向和判断
        4. 市场影响、热点和异常
        5. 行业影响、热点和异常
        6. 其他的市场重点要点信息

        新闻内容：
        {batch}
        """
        response = llm_client.one_chat(prompt)
        analysis_results.append(response)

    # 准备返回值
    results = []
    results.append(time_span)
    results.append("新闻分析结果：")
    for i, result in enumerate(analysis_results, 1):
        results.append(f"批次 {i} 分析：\n{result}\n")

    # 将结果保存到analysis_result变量
    analysis_result = "\n".join(results)

    # 使用LLM API生成markdown文件
    prompt = f"""请将以下新闻分析结果整理成markdown格式的报告。
    报告主要内容及markdown文件的结构如下：
    标题:xxxx年xx月xx日财经资讯分析报告
    (本次分析的时间范围：xxxx年xx月xx日xx点至xxxx年xx月xx日xx点)

    1. 主要市场趋势: 
       - 综合所有批次,识别出最重要、最具影响力的市场趋势。
       - 这些趋势如何相互关联或冲突?

    2. 金融市场动态:
       - 总结各个市场(如股票、债券、商品等)的整体表现和关键变动。
       - 识别出可能影响未来市场走向的关键因素。

    3. 市场情绪分析:
       - 综合评估整体市场情绪(如乐观、悲观、谨慎等)。
       - 分析情绪变化的原因和可能的影响。

    4. 热点和异常事件:
       - 列出所有批次中提到的主要热点和异常事件。
       - 评估这些事件对市场的短期和长期影响。

    5. 行业分析:
       - 识别受关注度最高或影响最大的行业。
       - 总结这些行业面临的机遇和挑战。

    6. 政策和监管影响:
       - 总结可能影响市场的主要政策或监管变化。
       - 分析这些变化可能带来的影响。

    7. 风险评估:
       - 基于所有分析结果,识别潜在的系统性风险或值得关注的风险因素。

    8. 前瞻性展望:
       - 根据当前分析,对短期和中期市场走势做出预测。
       - 提出投资者和市场参与者应该关注的关键点。

    请提供一个全面、深入、结构化的总结,整合所有批次的分析结果,突出最重要的发现和见解。

    需要总结的新闻内容摘要如下：
    {analysis_result}
    """

    response = reporter.one_chat(prompt)
    date_str = datetime.now().strftime("%Y%m%d%H%M%S")
    file = f"markdown/news/news{date_str}.md"
    # 创建或更新output.md文件
    with open(file, "w", encoding="utf-8") as f:
        f.write(response)

if __name__ == "__main__":
    runner()