export interface ExpertAnswer {
  version: number
  understanding: string
  core_points: string[]
  details: string
  conclusion: string
  confidence: number
  limitations: string[]
  modification_log: string[]
}

export interface CriticIssue {
  category: 'logic' | 'facts' | 'completeness' | 'relevance'
  severity: 'minor' | 'moderate' | 'major'
  description: string
  quote: string
}

export interface CriticReview {
  review_version: number
  overall_score: number
  passed: boolean
  issues: CriticIssue[]
  strengths: string[]
  suggestions: string[]
  confidence: number
}

export interface ModeratorSynthesis {
  decision: string
  analysis: string
  feedback_validation?: {
    valid_issues?: string[]
    invalid_issues?: string[]
  }
  improvement_guidance?: string
  iteration_summary?: string
}

export interface DebateIteration {
  round: number
  expert?: ExpertAnswer
  critic?: CriticReview
  synthesis?: ModeratorSynthesis
  finalAnswer?: string
}

export interface ModeratorInit {
  intent: string
  key_constraints: string[]
  complexity: 'simple' | 'moderate' | 'complex'
  complexity_reason: string
  decision: 'direct_answer' | 'delegate'
  direct_answer?: string
}

export type DebatePhase =
  | 'moderator_init'
  | 'expert_generate'
  | 'critic_review'
  | 'moderator_synthesize'
  | null

export type TerminationReason =
  | 'score_threshold'
  | 'explicit_pass'
  | 'max_iterations'
  | 'convergence'
  | 'simple_question'
  | null
