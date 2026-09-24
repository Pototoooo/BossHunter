"""Conservative employment-type checks, separate from campus/social recruitment."""
import re

def classify_employment(job):
    title = str(job.get('title') or '')
    jd = str(job.get('jd') or '')
    formal = bool(re.search(r'正式岗|全职岗位|非实习|不招实习|不接受实习', title))
    intern = bool(re.search(r'实习|\bintern(?:ship)?\b', title, re.I))
    explicit = re.search(r'(?:职位|岗位|工作|招聘|用工)(?:类型|性质)\s*[:：]\s*(实习|全职|兼职)', jd)
    if formal:
        return 'full_time'
    if explicit and explicit[1] == '全职':
        return 'unknown' if intern else 'full_time'
    if intern or (explicit and explicit[1] == '实习'):
        return 'internship'
    if re.search(r'兼职', title) or (explicit and explicit[1] == '兼职'):
        return 'part_time'
    if re.search(r'全职|正式岗', title):
        return 'full_time'
    # Daily pay, campus recruitment and prior internship experience are not proof.
    return 'unknown'

def internship_only(config):
    boss = config.get('platforms', {}).get('boss', {}).get('search', {})
    filters = boss.get('filters') if 'filters' in boss else config.get('search', {}).get('filters', {})
    value = (filters or {}).get('job_type', [])
    return value == '实习' or value == ['实习']

def internship_rejection(job, config):
    if str(job.get('source_platform') or 'boss') != 'boss' or not internship_only(config):
        return ''
    kind = classify_employment(job)
    if kind == 'internship':
        return ''
    return '仅实习：非实习岗位' if kind in {'full_time', 'part_time'} else '仅实习：职位类型待核实，禁止自动投递'
