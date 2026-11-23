"""Deliverable register. Status counts measure design deliverables, not journal usage."""
from design import uid
STATUS=['待设计','进行中','待确认','已完成']
def item(key,name,stage,output,depends='',status='待设计',next_step=''):
    return dict(id=key,name=name,stage=stage,output=output,depends=depends.split(),status=status,
                next=next_step or ('设计并提交'+name+'样稿'),evidence='')
def wish_items():
    return [
      item('brief','产品理念与范围','产品拆解','产品说明书 v0.1 与可调整的交付物清单',status='待确认',next_step='核对本次拆解与暂定产品名'),
      item('visual','书封视觉稿与三种版式','封面设计','完整书封的文字提案、元素关系与跨脊结构对照','brief','待确认','比较三个方向后选择或提出修改'),
      item('jacket','前封、书脊、封底联稿','封面设计','完整外封展开工程、独立文字和蒙版','visual',next_step='方向获确认后配素材；取得装订与实测脊宽后定尺寸'),
      item('stock','封面纸与工艺实验','封面工艺与用纸','纸样、印色及套位压凹或珠光效果的实物比较','jacket'),
      item('plates','封面生产交接','封面工艺与用纸','刀模对位、专色与工艺分版、接收方确认','stock'),
      item('architecture','内页结构与配页','内页设计','页面种类、顺序与比例原型；页数待测试','brief'),
      item('free','自由记录页','内页设计','支持自由书写、绘画与贴入素材的展开页','architecture'),
      item('review','周期主题发现页','内页设计','从近期记录发现重复主题的回顾页','architecture'),
      item('vision','月度愿景拼贴页','内页设计','图像、文字与尝试记录的版式','architecture'),
      item('annual','年度回望页','内页设计','对照早期愿望、变化与意外发现的跨页','architecture'),
      item('tags','开放主题贴纸','贴纸与索引','留白可自命名，一页可用多个标签的贴纸组与整张排版','brief'),
      item('index','主题索引页','贴纸与索引','个人关键词与关联页码的可追加索引','architecture tags'),
      item('link','贴纸与索引联动样例','贴纸与索引','从两处记录贴同一主题，经索引找回原页的完整样例','tags index free review'),
      item('innerstock','内页参考用纸与书写试样','内页工艺与用纸','书写、透印、拼贴后厚度与翻页测试','free vision'),
      item('stickerstock','贴纸材料与模切','内页工艺与用纸','面材、书写性、背胶、半穿刀及剥离试样','tags'),
      item('binding','装订与整册打样','内页工艺与用纸','配页、装订、脊宽回填和全册翻阅验证','architecture innerstock stickerstock link annual'),
    ]
def handoff(r):
    f=r['state']['workflow']; tasks=f['items'];done=sum(t['status']=='已完成' for t in tasks)
    lines=[f"# INKA+ · {f['name']}",f"工程版本 v{r['rev']}。共 {len(tasks)} 项，完成 {done} 项，余 {len(tasks)-done} 项。",
           '## 设计决定',f['visual'],f"封面方向：{f['choice'] or '未选择'}；生图许可：{'已确认当前方案' if f['approved'] else '等待用户确认'}。",
           '## 未决反馈',*[x['message'] for x in f['feedback']], '## 工作流与交付']
    for t in tasks:
        lines+= [f"- [{t['status']}] {t['stage']} / {t['name']}。交付：{t['output']}。依赖：{', '.join(t['depends']) or '无'}。下一步：{t['next']}。记录：{t['evidence'] or '暂无'}。"]
    lines+=['## 阶段记录',*[k+'：'+v for k,v in f['stageNotes'].items()],'## 产品原文',f['brief']]
    return '\n\n'.join(lines)

