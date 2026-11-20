"""生成面向阅读的文献大类，细分类型和原始元数据继续保留。"""
import re

CATEGORIES = {'review':'综述','research':'研究类','conference':'会议类','other':'其他／待确认'}

def classify_document(p, source):
    types = source.get('publication_types', [])
    indexed = set(types)
    title = p['title']
    detailed = (p.get('issue_review') or {}).get('reviewed_type') or p['article_type']
    if indexed & {'Published Erratum','Retracted Publication','Retraction of Publication','Expression of Concern'} or detailed=='correction_or_retraction':
        key,basis='other','更正、撤稿或关注声明，保留其证据角色，不归入研究成果'
    elif indexed & {'Congress','Meeting Abstract','Lecture'} or re.search(r'\b(meeting|conference|congress|summit)\b.{0,100}\breport\b|会议纪要|会议报告|大会报告|会议摘要',title,re.I):
        key,basis='conference','明确会议报告/会议摘要/讲座文章依据；不因会议曾报告同研究而改变完整论文类型'
    elif indexed & {'Practice Guideline','Guideline','Consensus Statement'} or re.search(r'\bconsensus (report|statement|guidance)\b|^中国.+(?:指南|共识)(?:（.*）|\(.*\))?$|专家共识$',title,re.I):
        key,basis='other','指南/共识单独保留；不将其直接当作综述或原创研究'
    elif indexed & {'Review','Systematic Review','Meta-Analysis'} or detailed=='review_or_guideline':
        key,basis='review','综述、系统评价或Meta分析，采用原始类型或已有摘要复核'
    elif indexed & {'Editorial','Letter','Comment','News','Interview','Biography'} or detailed=='commentary_or_letter':
        key,basis='other','评论、来信或其他非研究正文，保留具体类型'
    elif detailed in {'original_abstract_reviewed','original_reviewed','original_indexed','original_candidate','case_report'} or 'Case Reports' in indexed:
        key,basis='research','原创研究、研究候选或病例研究；具体设计、复核状态在详情保留'
    else:
        key,basis='other','现有元数据不足以稳定确认类型，不仅凭Journal Article认定研究类'
    return dict(category=key,label=CATEGORIES[key],basis=basis,detailed_type=detailed,publication_types=types)
