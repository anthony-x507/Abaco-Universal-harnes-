export type SkillStep = {
  id: string
  at: number
  action: string
}

export type Skill = {
  id: string
  title: string
  url: string
  steps: SkillStep[]
  createdAt: string
}

const STORAGE_KEY = 'universal-skills'

export function loadSkills(): Skill[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as Skill[]
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function saveSkills(skills: Skill[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(skills))
}

export function addSkill(skill: Skill) {
  saveSkills([skill, ...loadSkills()])
}

export function makeSkillId() {
  return `skl-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`
}
