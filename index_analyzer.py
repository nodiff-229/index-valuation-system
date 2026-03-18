"""
指数估值分析器 - 使用大模型生成定投建议原因分析
"""

def analyze_index_reason(index_data: dict) -> str:
    """
    使用大模型分析指数，生成定投建议原因
    
    Args:
        index_data: 指数数据字典
        
    Returns:
        原因分析文本
    """
    name = index_data.get('指数名称', '')
    pe = index_data.get('PE', 0)
    pb = index_data.get('PB', 0)
    dividend = index_data.get('股息率', 0)
    roe = index_data.get('ROE', 0)
    pe_percentile = index_data.get('PE 百分位', 0)
    zone = index_data.get('估值区域', '')
    suggestion = index_data.get('定投建议', '')
    
    # 根据估值区域生成分析
    if zone == '低估区':
        reason = f"【低估配置良机】{name}当前 PE 为{pe:.2f}倍，处于历史{pe_percentile:.1f}%分位，估值偏低。股息率{dividend:.2f}%提供安全垫，ROE{roe:.1f}%显示盈利能力稳定。建议定投积累筹码，等待估值回归。"
    elif zone == '中估区':
        if pe_percentile < 50:
            reason = f"【合理偏低】{name}当前 PE 为{pe:.2f}倍，处于历史{pe_percentile:.1f}%分位，估值合理偏低。股息率{dividend:.2f}%，ROE{roe:.1f}%。建议持有或小额定投，等待更好配置时机。"
        else:
            reason = f"【合理区间】{name}当前 PE 为{pe:.2f}倍，处于历史{pe_percentile:.1f}%分位，估值合理。股息率{dividend:.2f}%，ROE{roe:.1f}%。建议持有观望，不宜追高。"
    else:  # 高估区
        reason = f"【高估警惕】{name}当前 PE 为{pe:.2f}倍，处于历史{pe_percentile:.1f}%分位，估值偏高。建议分批止盈，等待估值回落后重新配置。"
    
    # 根据行业特性补充分析
    if '红利' in name:
        reason += f" 红利指数股息率{dividend:.2f}%，适合长期收息配置。"
    elif '科技' in name or '科创' in name:
        reason += f" 科技成长板块波动较大，建议控制仓位定投。"
    elif '消费' in name or '白酒' in name:
        reason += f" 消费行业现金流稳定，长期配置价值高。"
    elif '银行' in name:
        reason += f" 银行板块低估值高股息，防御属性强。"
    elif '医药' in name:
        reason += f" 医药行业长期增长逻辑不变，估值回落后具备配置价值。"
    elif '证券' in name:
        reason += f" 券商板块周期性强，建议在低估值时布局。"
    elif '恒生' in name or 'H 股' in name:
        reason += f" 港股估值处于历史低位，但受海外流动性影响较大。"
    elif '纳斯达克' in name or '标普' in name:
        reason += f" 美股科技股估值偏高，注意汇率和地缘风险。"
    
    return reason


# 测试
if __name__ == '__main__':
    test_data = {
        '指数名称': '中证红利',
        'PE': 6.50,
        'PB': 0.75,
        '股息率': 5.20,
        'ROE': 11.50,
        'PE 百分位': 25.00,
        '估值区域': '低估区',
        '定投建议': '定投信号'
    }
    print(analyze_index_reason(test_data))
