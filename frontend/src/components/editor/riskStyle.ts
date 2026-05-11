/**
 * 统一风险颜色计算。
 * 所有目录、正文、导出、badge 都必须调用这个函数。
 * 知网报告驱动模式下，reportRisk 优先于系统自检 riskScore。
 */

import type { DocumentBlock, ReportRiskData } from '../../types'

export interface RiskStyle {
  level: 'high' | 'medium' | 'low' | 'normal'
  bg: string
  border: string
  label: string
  source?: 'cnki' | 'internal'
}

/** 系统自检分数 → RiskStyle */
export function getRiskStyle(score: number | undefined): RiskStyle {
  const s = score ?? 0
  if (s >= 70) {
    return {
      level: 'high',
      bg: 'rgba(229, 57, 53, 0.18)',
      border: '#E53935',
      label: '高风险',
      source: 'internal',
    }
  }
  if (s >= 60) {
    return {
      level: 'medium',
      bg: 'rgba(251, 140, 0, 0.18)',
      border: '#FB8C00',
      label: '中风险',
      source: 'internal',
    }
  }
  if (s >= 30) {
    return {
      level: 'low',
      bg: 'rgba(142, 36, 170, 0.15)',
      border: '#8E24AA',
      label: '低风险',
      source: 'internal',
    }
  }
  return {
    level: 'normal',
    bg: 'rgba(67, 160, 71, 0.12)',
    border: '#43A047',
    label: '正常',
    source: 'internal',
  }
}

/** 知网报告风险 → RiskStyle */
export function getReportRiskStyle(reportRisk: ReportRiskData | undefined): RiskStyle | null {
  if (!reportRisk) return null
  switch (reportRisk.riskLevel) {
    case 'high':
      return {
        level: 'high',
        bg: 'rgba(229, 57, 53, 0.22)',
        border: '#E53935',
        label: '高风险（知网）',
        source: 'cnki',
      }
    case 'medium':
      return {
        level: 'medium',
        bg: 'rgba(251, 140, 0, 0.22)',
        border: '#FB8C00',
        label: '中风险（知网）',
        source: 'cnki',
      }
    case 'low':
      return {
        level: 'low',
        bg: 'rgba(142, 36, 170, 0.18)',
        border: '#8E24AA',
        label: '低风险（知网）',
        source: 'cnki',
      }
    default:
      return null
  }
}

/** 统一入口：优先 reportRisk，其次 internal score */
export function getEffectiveRiskStyle(block: DocumentBlock): RiskStyle {
  const reportStyle = getReportRiskStyle(block.reportRisk)
  if (reportStyle) return reportStyle
  return getRiskStyle(block.riskScore)
}

/** 获取有效风险等级字符串（用于 CSS class） */
export function getEffectiveRiskLevel(block: DocumentBlock): 'high' | 'medium' | 'low' | 'normal' {
  return getEffectiveRiskStyle(block).level
}

/** Word 导出用的浅色系背景色 */
export function getRiskHexForDocx(score: number | undefined): string {
  const s = score ?? 0
  if (s >= 70) return 'FFCDD2'
  if (s >= 60) return 'FFE0B2'
  if (s >= 30) return 'E1BEE7'
  return 'C8E6C9'
}

/** Word 导出：reportRisk 优先 */
export function getEffectiveRiskHexForDocx(block: DocumentBlock): string {
  if (block.reportRisk) {
    switch (block.reportRisk.riskLevel) {
      case 'high': return 'FFCDD2'
      case 'medium': return 'FFE0B2'
      case 'low': return 'E1BEE7'
      default: return 'C8E6C9'
    }
  }
  return getRiskHexForDocx(block.riskScore)
}
