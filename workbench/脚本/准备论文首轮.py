"""解析首轮已保存PubMed及中文官方目录索引，不联网、不写数据库。"""
from pathlib import Path
from datetime import date
import xml.etree.ElementTree as E
import json,re,hashlib,calendar
ROOT=Path(__file__).resolve().parents[1];RAW=ROOT/'原始资料/论文首轮_2026-11-17';START='2026-08-17';END='2026-11-17'
def text(node):return ' '.join(''.join(node.itertext()).split()) if node is not None else ''
def xml_date(node):
 if node is None:return None,None
 year=node.findtext('Year');month=node.findtext('Month');day=node.findtext('Day')
 if not year:
  z=re.search(r'(20\d{2})(?:\s+([A-Za-z]{3}|\d{1,2}))?',text(node))
  if not z:return None,None
  year,month=z.group(1),z.group(2)
 if not month:return year,'year'
 if not month.isdigit():month=str(list(calendar.month_abbr).index(month[:3].title())) if month[:3].title() in list(calendar.month_abbr) else None
 if not month:return year,'year'
 return f'{int(year):04d}-{int(month):02d}'+(f'-{int(day):02d}' if day and day.isdigit() else ''),'day' if day and day.isdigit() else 'month'
def in_window(d,precision):
 if not d:return 'date_pending'
 lo=d if precision=='day' else d+'-01' if precision=='month' else d+'-01-01';hi=d if precision=='day' else d+'-'+str(calendar.monthrange(int(d[:4]),int(d[5:7]))[1]) if precision=='month' else d+'-12-31'
 if hi<START or lo>END:return 'outside'
 if lo<START or hi>END:return 'boundary_pending'
 return 'in_window'
manifest=json.loads((RAW/'采集清单.json').read_text());core=set(manifest['core_ids']);papers={}
for f in sorted(RAW.glob('PubMed*.xml')):
 for elem in E.parse(f).getroot().findall('PubmedArticle'):
  med=elem.find('MedlineCitation');a=med.find('Article');pmid=med.findtext('PMID');ids={n.get('IdType'):n.text for n in elem.findall('PubmedData/ArticleIdList/ArticleId')};doi=(ids.get('doi') or '').lower().strip();authors=[]
  for i,au in enumerate(a.findall('AuthorList/Author')):
   authors.append(dict(ordinal=i+1,name=(au.findtext('ForeName','')+' '+au.findtext('LastName','')).strip() or au.findtext('CollectiveName',''),collective=au.find('CollectiveName') is not None,initials=au.findtext('Initials'),affiliations=[text(z) for z in au.findall('AffiliationInfo/Affiliation')],orcid=next((x.text for x in au.findall('Identifier') if x.get('Source')=='ORCID'),None),corresponding_status='not_established'))
  types=[text(x) for x in a.findall('PublicationTypeList/PublicationType')];title=text(a.find('ArticleTitle'));abstract=[dict(label=x.get('Label') or x.get('NlmCategory') or '',text=text(x)) for x in a.findall('Abstract/AbstractText')];full=' '.join(x['text'] for x in abstract)
  epub=a.find('ArticleDate[@DateType="Electronic"]')
  if epub is None:epub=elem.find('PubmedData/History/PubMedPubDate[@PubStatus="epublish"]')
  online,op=xml_date(epub);issue,ip=xml_date(a.find('Journal/JournalIssue/PubDate'));chosen,precision=(online,op) if online else (issue,ip)
  t=' '.join(types).lower();kind='type_pending';basis='仅Journal Article不足以确认原创研究；待复核'
  if any(x in t for x in ['published erratum','retracted publication','retraction of publication']) or re.match(r'(correction|erratum|retraction)\b',title,re.I):kind,basis='correction_or_retraction','PubMed类型或题名明确更正/撤稿'
  elif any(x in t for x in ['review','meta-analysis','guideline','consensus']):kind,basis='review_or_guideline','PubMed文献类型：'+','.join(types)
  elif any(x in t for x in ['editorial','comment','letter','news','interview','biography']):kind,basis='commentary_or_letter','PubMed文献类型：'+','.join(types)
  elif 'case reports' in t:kind,basis='case_report','PubMed病例报告类型'
  elif any(x in t for x in ['randomized controlled trial','clinical trial','observational study','comparative study','evaluation study']):kind,basis='original_indexed','PubMed研究类型：'+','.join(types)
  elif any(x['label'].upper() in ['METHODS','RESEARCH DESIGN AND METHODS','RESULTS','FINDINGS'] for x in abstract) and len(full)>150:kind,basis='original_candidate','结构化方法/结果摘要，原创候选待人工复核'
  elif len(full)>200 and re.search(r'\b(we (investigated|identified|examined|found|show|used|assessed|evaluated|conducted)|this study|in this study)\b',full,re.I):kind,basis='original_candidate','摘要含研究设计/结果描述，原创候选待人工复核'
  papers[pmid]=dict(paper_id='PMID:'+pmid,pmid=pmid,doi=doi or None,pmcid=ids.get('pmc'),title=title,journal=text(a.find('Journal/Title')),journal_abbr=a.findtext('Journal/ISOAbbreviation'),source_tier='core' if pmid in core else 'supplement',language=[text(x) for x in a.findall('Language')],publication_date=chosen,date_precision=precision,date_basis='electronic' if online else 'issue_fallback',online_date=online,issue_date=issue,window_status=in_window(chosen,precision),article_type=kind,type_basis=basis,publication_types=types,abstract=abstract,authors=authors,source_url='https://pubmed.ncbi.nlm.nih.gov/'+pmid+'/',publisher_url='https://doi.org/'+doi if doi else None,raw_path=str(f.relative_to(ROOT)),source_locator='PubmedArticle[PMID='+pmid+']',reading_level='indexed_abstract' if full else 'metadata_only',mesh=[text(x.find('DescriptorName')) for x in med.findall('MeshHeadingList/MeshHeading')],article_links=[dict(relation=x.get('RefType'),pmid=x.findtext('PMID')) for x in med.findall('CommentsCorrectionsList/CommentsCorrections')])
# 中文官方目录/检索索引：只提取有明确题名与期刊期次的记录；页面空壳不等于零文章。
cn={}
for f in RAW.glob('中文*.txt'):
 s=f.read_text();s=re.sub(r'(?m)^L\d+: ?','',s)
 for block in s.split('--------------------------------------------------------------------------------'):
  url_match=re.search(r'^.*?\((https://(?:cs\.medjournals\.cn|zhtnbzz\.yiigle\.com|zhnfmdxzz\.yiigle\.com)[^\n]+)\)',block,re.M)
  source_url=url_match.group(1) if url_match else None
  if not source_url:continue
  header=re.search(r'(?:出版日期[：:]?\s*|\n)(2026-\d{2}-\d{2})',block)
  chunks=re.split(r'(?m)^###\s*',block)
  for chunk in chunks[1:]:
   lines=chunk.splitlines();title=re.sub(r'^【\d+†|】$','',lines[0]).strip();jm=re.search(r'(中华糖尿病杂志|中华内分泌代谢杂志)\s*2026年\s*(?:第)?(?:18|42)卷\s*(?:第)?(\d{2})期',chunk)
   if not jm or not title or title in ['MedNexus','中华糖尿病杂志','中华内分泌代谢杂志','最新发表','优先出版','智能推荐','编辑推荐Featured Articles']:continue
   # 必须在题名后的短距离内出现该文的期刊行，避免将导航标题识别成文章。
   if jm.start()>600:continue
   journal,month=jm.group(1),jm.group(2);before=chunk[len(lines[0]):jm.start()];names=re.sub(r'\s+',' ',before).strip();doi_match=re.search(r'DOI:\s*(10\.3760/[^\s]+)',chunk);doi=doi_match.group(1).rstrip('。;,') if doi_match else None
   if len(names)>160 or '摘要' in names:continue
   pubdate=header.group(1) if header and header.group(1)[5:7]==month else '2026-'+month;prec='day' if len(pubdate)==10 else 'month'
   key=doi or hashlib.sha256((journal+'|'+month+'|'+title).encode()).hexdigest()[:20]
   prev=cn.get((journal,title));record=dict(paper_id='DOI:'+doi if doi else 'CN:'+key,pmid=None,doi=doi,pmcid=None,title=title,journal=journal,journal_abbr=journal,source_tier='domestic_partial',language=['chi'],publication_date=pubdate,date_precision=prec,date_basis='issue_directory',online_date=None,issue_date=pubdate,window_status=in_window(pubdate,prec),article_type='type_pending',type_basis='中文目录片段，需核原栏目及文章类型',publication_types=[],abstract=[],authors=[dict(ordinal=i+1,name=n,collective=False,initials=None,affiliations=[],orcid=None,corresponding_status='not_established') for i,n in enumerate(names.split()) if n not in ['等','等。']],source_url=source_url,publisher_url='https://doi.org/'+doi if doi else None,raw_path=str(f.relative_to(ROOT)),source_locator='目录题名：'+title,reading_level='directory_excerpt',mesh=[],article_links=[])
   if prev is None or (doi and not prev['doi']) or (prec=='day' and prev['date_precision']!='day'):cn[(journal,title)]=record
# 搜索索引有时省略Markdown标题符号；补读明确的“题名—作者—期刊期次”相邻行。
import copy
for f in RAW.glob('中文*.txt'):
 s=re.sub(r'(?m)^L\d+: ?','',f.read_text())
 for block in s.split('--------------------------------------------------------------------------------'):
  um=re.search(r'^.*?\((https://cs\.medjournals\.cn[^\n]+)\)',block,re.M)
  if not um:continue
  for m in re.finditer(r'(中华糖尿病杂志|中华内分泌代谢杂志)\s*2026年\s*(?:第)?(?:18|42)卷\s*(?:第)?(\d{2})期',block):
   prev=[z.strip() for z in block[:m.start()].splitlines() if z.strip()]
   if len(prev)<2:continue
   names,title=prev[-1],re.sub(r'^【\d+†|】$','',re.sub(r'^###\s*','',prev[-2])).strip()
   if len(title)<10 or len(title)>160 or len(names)>130 or any(z in title+names for z in ['[wordlim','http','Source:','DOI:','摘要','2026年','Crawled:','出版日期']):continue
   if not re.fullmatch(r'[\u4e00-\u9fffA-Za-z\s·]+',names):continue
   journal,month=m.group(1),m.group(2);dm=re.search(r'DOI:\s*(10\.3760/[^\s]+)',block[m.end():m.end()+250]);doi=dm.group(1) if dm else None
   key=(journal,title)
   if key in cn:continue
   template=copy.deepcopy(next(iter(cn.values())));d='2026-'+month
   template.update(paper_id='DOI:'+doi if doi else 'CN:'+hashlib.sha256((journal+'|'+month+'|'+title).encode()).hexdigest()[:20],doi=doi,title=title,journal=journal,journal_abbr=journal,publication_date=d,date_precision='month',date_basis='issue_index_month',online_date=None,issue_date=d,window_status=in_window(d,'month'),authors=[dict(ordinal=i+1,name=n,collective=False,initials=None,affiliations=[],orcid=None,corresponding_status='not_established') for i,n in enumerate(names.split()) if n!='等'],source_url=um.group(1),publisher_url='https://doi.org/'+doi if doi else None,raw_path=str(f.relative_to(ROOT)),source_locator='相邻题名/作者/期次：'+title)
   cn[key]=template
# 跨目录同题名同刊优先带DOI记录；没有可靠标识不跨语种合并。
allpapers=list(papers.values())+list(cn.values())
curation=json.loads((RAW/'人工核对与进展摘要.json').read_text())
for x in curation['additional_directory_records']:
 prev=next((p for p in allpapers if p['doi']==x['doi'] or (p['journal']==x['journal'] and p['title']==x['title'])),None)
 record=copy.deepcopy(prev or next(iter(cn.values())))
 record.update(paper_id='DOI:'+x['doi'],pmid=None,doi=x['doi'],title=x['title'],journal=x['journal'],journal_abbr=x['journal'],publication_date=x['date'],date_precision='day',date_basis='issue_directory',online_date=None,issue_date=x['date'],window_status=in_window(x['date'],'day'),article_type=x['type'],type_basis='本轮已读官方目录/摘要人工核对（AI初稿）',authors=[dict(ordinal=i+1,name=n,collective=False,initials=None,affiliations=[],orcid=None,corresponding_status='not_established') for i,n in enumerate(x['authors'].split())],source_url=x['source_url'],publisher_url='https://doi.org/'+x['doi'],raw_path=str((RAW/'人工核对与进展摘要.json').relative_to(ROOT)),source_locator=x['source_locator'],summary_curated=x['summary'])
 if prev:allpapers.remove(prev)
 allpapers.append(record)
for p in allpapers:
 if p['paper_id'] in curation.get('date_overrides',{}):
  x=curation['date_overrides'][p['paper_id']];p.update(publication_date=x['date'],online_date=x['date'],date_precision='day',date_basis=x['basis'],window_status=in_window(x['date'],'day'),date_evidence=x)
 if p['language']==['chi'] and p['article_type']=='type_pending':
  if re.search(r'综述|研究进展|系统评价|Meta分析|共识|指南|要点与解读|结果解读|中文导读',p['title'],re.I):p['article_type']='review_or_guideline';p['type_basis']='中文题名明确综述/指南/解读，待栏目复核'
  elif re.search(r'1例|一例|家系|例报告',p['title']):p['article_type']='case_report';p['type_basis']='中文题名病例/家系线索，待栏目复核'
unique={};duplicates=[]
for p in allpapers:
 if p['paper_id'] in unique:duplicates.append(dict(paper_id=p['paper_id'],title=p['title'],raw_path=p['raw_path']))
 else:unique[p['paper_id']]=p
allpapers=list(unique.values());(RAW/'标识去重记录.json').write_text(json.dumps(duplicates,ensure_ascii=False,indent=2));(RAW/'论文结构化初稿.json').write_text(json.dumps(allpapers,ensure_ascii=False,indent=2));
from collections import Counter
print(json.dumps(dict(total=len(allpapers),pubmed=len(papers),chinese=sum(x['language']==['chi'] for x in allpapers),types=Counter(x['article_type'] for x in allpapers),window=Counter(x['window_status'] for x in allpapers)),ensure_ascii=False));
