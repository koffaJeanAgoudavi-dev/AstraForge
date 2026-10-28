import { ProjectSpec, ProviderProfile } from '../types';

const STORAGE_KEYS = {
  PROJECTS: 'astraforge_projects_v1',
  ACTIVE_PROJECT_ID: 'astraforge_active_project_id',
  PROFILES: 'astraforge_provider_profiles_v1',
};

export const DEFAULT_PROFILES: ProviderProfile[] = [
  {
    role: 'architect',
    preferredProviders: ['openai', 'gemini', 'deepseek', 'mistral', 'groq', 'cerebras'],
    temperature: 0.1,
    model: 'gpt-4o / gemini-2.5-pro',
  },
  {
    role: 'developer',
    preferredProviders: ['deepseek', 'mistral', 'openai', 'gemini', 'cerebras', 'groq'],
    temperature: 0.1,
    model: 'deepseek-coder / claude-3-5-sonnet',
  },
  {
    role: 'tester',
    preferredProviders: ['cerebras', 'groq', 'deepseek', 'mistral', 'gemini', 'openai'],
    temperature: 0.0,
    model: 'cerebras-llama3.1-70b / groq-mixtral',
  },
  {
    role: 'reviewer',
    preferredProviders: ['openai', 'deepseek', 'gemini', 'mistral', 'cerebras', 'groq'],
    temperature: 0.0,
    model: 'gpt-4o / gemini-2.5-flash',
  },
];

export const INITIAL_PROJECT: ProjectSpec = {
  id: 'proj-ai-agency-landing',
  name: 'Landing page — AI Agency',
  description: 'Crée une landing page moderne pour une agence IA avec une section hero, services, témoignages et formulaire de contact.',
  requirements: [
    'Section Hero percutante avec badge dynamique et bouton CTA',
    'Grille de 3 services d’ingénierie logicielle IA',
    'Boîte de contact avec validation côté client',
    'Design sombre cohérent et responsive',
  ],
  status: 'created',
  type: 'web',
  createdAt: new Date().toISOString(),
};

export class AppStateStorage {
  static getProjects(): ProjectSpec[] {
    try {
      const data = localStorage.getItem(STORAGE_KEYS.PROJECTS);
      if (data) {
        return JSON.parse(data);
      }
    } catch {
      // fallback
    }
    return [INITIAL_PROJECT];
  }

  static saveProjects(projects: ProjectSpec[]): void {
    try {
      localStorage.setItem(STORAGE_KEYS.PROJECTS, JSON.stringify(projects));
    } catch (e) {
      console.error('Failed to save projects to localStorage', e);
    }
  }

  static getProfiles(): ProviderProfile[] {
    try {
      const data = localStorage.getItem(STORAGE_KEYS.PROFILES);
      if (data) {
        return JSON.parse(data);
      }
    } catch {
      // fallback
    }
    return DEFAULT_PROFILES;
  }

  static saveProfiles(profiles: ProviderProfile[]): void {
    try {
      localStorage.setItem(STORAGE_KEYS.PROFILES, JSON.stringify(profiles));
    } catch (e) {
      console.error('Failed to save profiles to localStorage', e);
    }
  }
}
