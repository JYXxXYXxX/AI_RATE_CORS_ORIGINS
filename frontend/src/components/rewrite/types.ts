import type {
  DocumentBlock,
  RewriteWorkspaceMetrics,
  RewriteWorkspaceRiskItem,
  RewriteWorkspaceSectionNode,
} from '../../types'

export type RiskLevel = 'high' | 'medium' | 'low' | 'normal'
export type RiskStatus = RewriteWorkspaceRiskItem['status']

export interface RewriteSection extends RewriteWorkspaceSectionNode {
  level: number
  paragraphIds: string[]
}

export interface RewriteParagraph {
  paragraphId: string
  blockId: string
  sectionId: string
  sectionTitle: string
  type: DocumentBlock['type']
  text: string
  html?: string
  displayOrder: number
  charCount: number
  riskId?: string
  sourceMap?: DocumentBlock['sourceMap']
}

export interface RewriteRiskItem extends Omit<RewriteWorkspaceRiskItem, 'status'> {
  status: RiskStatus
}

export interface RewriteMetricsState extends RewriteWorkspaceMetrics {
  duplicatePercent: number
  wordCount: number
}

export interface RewriteHistoryEntry {
  riskId: string
  paragraphId: string
  beforeText: string
  afterText: string
  beforeStatus: RiskStatus
  afterStatus: RiskStatus
}
