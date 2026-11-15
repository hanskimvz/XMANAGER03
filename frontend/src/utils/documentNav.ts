import type { Router } from 'vue-router'

export function navigateToDocument(router: Router, docId: number, docType: string) {
  const tab = docType === 'QUOTATION' ? 'quotations' : docType === 'CI' ? 'ci' : 'pi'
  router.push({
    path: '/sales',
    query: { tab, open_doc_id: String(docId) },
  })
}
