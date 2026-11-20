"""领域热点只读投影：沿用当前主议题分类，人物角色不参与数量计算。"""
from urllib.parse import quote

TALK_FORMATS = {'大会报告', '专题报告', '论文发言'}


def build_hotspots(c, entries, admissions):
    topics = {}
    conferences = []
    reports = []
    people = {}
    for entry in entries:
        cid = entry['conference_id']
        vid = entry['analysis_version']['analysis_version_id']
        conf = {k: entry[k] for k in ('conference_id', 'year', 'abbreviation', 'region',
                'name_original', 'tier_label', 'view_url', 'topic_url', 'coverage_url',
                'source_snapshot_label', 'coverage_note', 'classification_label')}
        assert conf['region'] in ('domestic', 'international'), cid
        conf['admission'] = admissions.get(cid, dict(status='supplement', basis='尚未完成会议纳入复核，仅作补充材料，不进入榜单计算。'))
        assert conf['admission']['status'] in ('main','trial','supplement')
        conf['cohorts'] = {}
        for key, condition in [('talks', "report_format IN ('大会报告','专题报告','论文发言')"),
                               ('posters', "report_format IN ('海报报告','晚期突破海报')"), ('all', '1=1')]:
            total = c.execute(f'SELECT COUNT(*) FROM reports WHERE conference_id=? AND {condition}', (cid,)).fetchone()[0]
            classified = c.execute(f'''SELECT COUNT(DISTINCT r.report_id) FROM reports r
                JOIN report_classifications rc USING(report_id)
                WHERE r.conference_id=? AND rc.analysis_version_id=? AND rc.eligible=1 AND {condition}''', (cid, vid)).fetchone()[0]
            conf['cohorts'][key] = dict(total=total, classified=classified, outside=total-classified)
        conferences.append(conf)
        # 跨会对应来自已存显式映射，不由名称相似度或讲者身份推断。
        if entry['analysis_version']['analysis_kind'] == 'topic_quantity':
            scope = c.execute('''SELECT t.*,x.width_status,x.boundary_text,x.evidence_gaps AS scope_gaps,
                t.topic_id AS canonical_id FROM research_topics t JOIN topic_scope_review_targets x
                ON t.topic_id=x.new_topic_id WHERE x.analysis_version_id=?''', (vid,)).fetchall()
            speaker_view = 'v_cds_quantity_speaker_talks'
        else:
            scope = c.execute('''SELECT t.*,x.width_status,x.boundary_text,x.evidence_gaps AS scope_gaps,
                x.template_topic_id AS canonical_id FROM research_topics t JOIN conference_topic_scope x
                USING(topic_id) WHERE x.analysis_version_id=?''', (vid,)).fetchall()
            speaker_view = 'v_ada_quantity_speaker_talks'
        canonical_map = {}
        for row in scope:
            x = dict(row)
            canonical = x['canonical_id']
            assert canonical, x['topic_id']
            canonical_map[x['topic_id']] = canonical
            target = dict(c.execute('SELECT * FROM research_topics WHERE topic_id=?', (canonical,)).fetchone())
            board = dict(c.execute('SELECT * FROM research_topics WHERE topic_id=?', (target['parent_topic_id'],)).fetchone())
            topic = topics.setdefault(canonical, dict(topic_id=canonical, name=target['name'],
                research_question=target['research_question'], board_id=board['topic_id'],
                board_name=board['name'], width_status=x['width_status'], mappings=[]))
            topic['mappings'].append(dict(conference_id=cid, local_topic_id=x['topic_id'],
                boundary_text=x['boundary_text'], scope_gaps=x['scope_gaps'],
                classification_status=entry['analysis_version']['review_status'],
                detail_url=entry['view_url']+'#topic/'+quote(x['topic_id'], safe='')))
        participants = {}
        for row in c.execute(f'SELECT * FROM {speaker_view} WHERE conference_id=?', (cid,)):
            x = dict(row)
            pid = x['person_id']
            # 同名跨会议身份不自动合并。
            key = cid + '|' + pid
            participants.setdefault(x['report_id'], set()).add(key)
            if key not in people:
                tier = dict(c.execute('SELECT * FROM v_speaker_tiers WHERE conference_id=? AND person_id=?', (cid, pid)).fetchone())
                people[key] = {k: tier.get(k) for k in ('person_id','display_name','institution_source',
                    'tier_code','tier_label','domain_scope','tenure_status','assessment_status','rationale','evidence_gaps')}
                people[key]['key'] = key
                people[key]['conference_id'] = cid
                people[key]['detail_url'] = entry['view_url']+'#speaker/'+quote(pid, safe='')
        originals = [dict(x) for x in c.execute('''SELECT relative_path,source_url,material_kind FROM source_materials
            WHERE relative_path LIKE ? AND material_kind IN ('official_agenda_html','official_program_pdf')''',
            ('原始资料/'+cid+'/%',))]
        conf['originals'] = [dict(x, local_url=quote('../'+x['relative_path'], safe='/')) for x in originals]
        for row in c.execute('''SELECT r.*,rc.primary_topic_id,rc.classification_basis FROM v_report_detail r
                JOIN report_classifications rc USING(report_id)
                WHERE r.conference_id=? AND rc.analysis_version_id=? AND rc.eligible=1
                ORDER BY r.local_date,r.start_time,r.source_report_code''', (cid, vid)):
            x = dict(row)
            assert x['primary_topic_id'] in canonical_map, x['primary_topic_id']
            reports.append(dict(report_id=x['report_id'], conference_id=cid,
                topic_id=canonical_map[x['primary_topic_id']], title=x['title_original'],
                report_format=x['report_format'], cohort='talks' if x['report_format'] in TALK_FORMATS else 'posters',
                code=x['source_report_code'], date=x['local_date'], time=x['time_original'],
                session=x['session_title'], source_url=x['source_url'], source_locator=x['source_locator'],
                classification_basis=x['classification_basis'],
                speaker_keys=sorted(participants.get(x['report_id'], set())),
                detail_url=entry['view_url']+'#report/'+quote(x['report_id'], safe='')))
    assert len(reports) == len({r['report_id'] for r in reports})
    boards = {t['board_id']:dict(board_id=t['board_id'],name=t['board_name']) for t in topics.values()}
    return dict(version='domain-attention-v2-balanced-regions', conferences=conferences,
        boards=sorted(boards.values(),key=lambda x:x['board_id']),
        topics=sorted(topics.values(),key=lambda x:x['topic_id']), reports=reports, people=list(people.values()),
        method=dict(label='综合会议关注度', conference_share='议题去重报告数 ÷ 本会议同类已归类报告数 × 100%',
            overall='国内关注度＝国内纳入会议的议题占比均值；国际关注度同理。综合关注度＝国内关注度×50%＋国际关注度×50%；各地域内部每场会议等权。',
            zero='同类已归类分母大于0但未归入本议题时，记已归类范围内0条；仍可能有待归类报告，不能断言整场会议没有讨论。同类分母为0的会议不参与均值；国内或国际任一侧无可用会议，综合关注度留空，不将另一侧改为100%。',
            denominator='分母限同年、同报告类型的已归类去重报告；研究板块、关键词和议题筛选不改变分母。国内榜、国际榜各自显示本地域报告和讲者，综合榜汇集两侧。',
            boards='研究板块关注度：先按板块内报告ID去重，除以该会议同类已归类报告数，再按国内、国际及50/50综合口径计算；随当前榜单降序排列。板块不取议题排名平均，不按议题个数加分，搜索及板块选择不改变其计算。',
            dedup='一条报告按报告ID去重，只计入当前版本的一个主议题；ADA同摘要重复场次已在入库时合并。跨会议报告分别计作会议讨论，不声称为独立研究。',
            alignment='沿用当前CDS议题目录及ADA显式模板映射；宽窄和跨会归类仍待人工校准。',
            roles='角色依已有资料暂定，保留角色领域及历任/候任状态；人物角色不参与关注度加权。',
            admission='主榜纳入条件：会议届次、学术覆盖分类和资料版本明确；取得完整或可界定的官方日程范围，非精选摘录；报告类型统一、报告去重可核、统一议题映射可追溯；列明未解析/另列/待归类内容，并复核遗漏是否集中于某类主题。通过复核后标为正式纳入。只有选摘或覆盖不可界定的材料仅补充展示，不参与主榜。',
            trial='当前CDS和ADA均明确配置为试算纳入，保留已有资料用于验证框架；题名归类、跨会映射及待归类分布尚未完成最终人工校准，不能标成已满足正式可比条件。新增会议默认仅补充，完成纳入复核后才配置进入榜单；不使用未经验证的覆盖率阈值自动判定合格。',
            coverage='分类覆盖率＝同类已归类报告数÷同类已入库报告数。它反映入库后的归类覆盖，不是官网全部资料的采集完整率。分别记录资料版本、入库量、已归类量、另列/待归类量和遗漏原因；会前日程不当作实际报告结果。低覆盖及缺失分布差异仍会影响排序，50/50仅解决地域会议数量权重失衡。',
            limits='仅反映已纳入会议的议程关注，不表示升温、研究成熟度或临床可用性。新增会议/版本、专题会议构成及归类覆盖仍会改变排序；本轮国内、国际各1场，改为50/50后当前综合数值基本不变。判断升降趋势须用固定会议组合和相同报告范围。'))
