/**
 * 앱 설정 API (v0.49.0)
 * - 지출결의서 기본 집행 담당(disbursement approvers)
 */
import apiClient from './client'

export interface DisbApprover {
  id: number
  name: string
  username: string
  position?: string | null
  department?: string | null
}

// 회사 은행 계좌(통화별)
export interface CompanyBankAccount {
  currency: string
  bank_name?: string | null
  bank_address?: string | null
  swift_code?: string | null
  account_name?: string | null
  account_number?: string | null
  is_default: boolean
}

export const settingsApi = {
  // 지출결의서 기본 집행 담당(순서대로) — 작성 시 결재선 자동채움
  getDisbursementApprovers: async (): Promise<DisbApprover[]> => {
    const res = await apiClient.get('/settings/disbursement-approvers')
    return res.data.approvers || []
  },
  // [관리자] 집행 담당 지정/변경 (user_ids 순서 = 결재선 순서)
  setDisbursementApprovers: async (userIds: number[]): Promise<DisbApprover[]> => {
    const res = await apiClient.put('/settings/disbursement-approvers', { user_ids: userIds })
    return res.data.approvers || []
  },
  // 회사 은행 계좌(통화별) — 문서 작성 시 통화에 맞는 계좌 자동채움
  getCompanyBankAccounts: async (): Promise<CompanyBankAccount[]> => {
    const res = await apiClient.get('/settings/company-bank-accounts')
    return res.data.accounts || []
  },
  // [관리자] 통화별 회사 계좌 저장
  setCompanyBankAccounts: async (accounts: CompanyBankAccount[]): Promise<CompanyBankAccount[]> => {
    const res = await apiClient.put('/settings/company-bank-accounts', { accounts })
    return res.data.accounts || []
  },
}
