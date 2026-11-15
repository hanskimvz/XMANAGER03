/**
 * 실시간(타이핑 감지) 검색용 debounce 헬퍼.
 * 검색 입력의 @input 에 연결하면 마지막 타이핑 후 delay(ms) 뒤 fn 을 1회 호출.
 * 각 화면의 검색 함수는 보통 page/skip 을 1페이지로 리셋한 뒤 서버 조회하므로,
 * 서버 페이지네이션이 필터 반영 후 계산돼 "1페이지부터 제한개수만큼" 채워진다.
 *
 * 사용:
 *   const debouncedSearch = useDebouncedSearch(searchXxx)   // 기존 검색 함수 그대로
 *   <input @input="debouncedSearch" @keyup.enter="searchXxx" ... />
 */
export function useDebouncedSearch(fn: () => void, delay = 300): () => void {
  let timer: ReturnType<typeof setTimeout> | null = null
  return () => {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => fn(), delay)
  }
}
