/**
 * 统一风险颜色计算。
 * 所有目录、正文、导出、badge 都必须调用这个函数。
 */

export interface RiskStyle {
  level: 'high' | 'medium' | 'low' | 'normal'
  bg: string
  border: string
  label: string
}

export function getRiskStyle(score: number | undefined): RiskStyle {
  const s = score ?? 0
  if (s >= 70) {
    return {
      level: 'high',
      bg: 'rgba(229, 57, 53, 0.18)',
      border: '#E53935',
      label: '高风险',
    }
  }
  if (s >= 60) {
    return {
      level: 'medium',
      bg: 'rgba(251, 140, 0, 0.18)',
      border: '#FB8C00',
      label: '中风险',
    }
  }
  if (s >= 30) {
    return {
      level: 'low',
      bg: 'rgba(142, 36, 170, 0.15)',
      border: '#8E24AA',
      label: '低风险',
    }
  }
  return {
    level: 'normal',
    bg: 'rgba(67, 160, 71, 0.12)',
    border: '#43A047',
    label: '正常',
  }
}

/** Word 导出用的浅色系背景色 */
export function getRiskHexForDocx(score: number | undefined): string {
  const s = score ?? 0
  if (s >= 70) return 'FFCDD2'
  if (s >= 60) return 'FFE0B2'
  if (s >= 30) return 'E1BEE7'
  return 'C8E6C9'
}
