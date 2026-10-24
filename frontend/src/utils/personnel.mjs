const nameCollator = new Intl.Collator('fa', { sensitivity: 'base', numeric: true })
const normalizeName = (value) => String(value || '').trim().replace(/ي/g, 'ی').replace(/ك/g, 'ک')

export function filterPersonnel(workers, status = 'active', search = '') {
  const query = normalizeName(search).toLocaleLowerCase('fa')
  return workers.filter((worker) => {
    const active = worker.is_available === true && worker.is_active !== false
    if (status === 'active' && !active) return false
    if (status === 'inactive' && active) return false
    return normalizeName(`${worker.full_name || ''} ${worker.username || ''} ${worker.phone || ''} ${worker.role || ''}`)
      .toLocaleLowerCase('fa').includes(query)
  }).sort((a, b) => nameCollator.compare(
    normalizeName(a.full_name || a.username), normalizeName(b.full_name || b.username)
  ) || Number(a.id) - Number(b.id))
}
