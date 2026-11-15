import type { Extensions } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import { TextStyle, Color, FontSize } from '@tiptap/extension-text-style'
import Highlight from '@tiptap/extension-highlight'
import Image from '@tiptap/extension-image'
import { Placeholder } from '@tiptap/extensions'

export const FONT_SIZE_OPTIONS = [
  { label: '12', value: '12px' },
  { label: '14', value: '14px' },
  { label: '16', value: '16px' },
  { label: '18', value: '18px' },
  { label: '20', value: '20px' },
  { label: '24', value: '24px' },
]

export const MAX_EDITOR_IMAGE_SIZE = 2 * 1024 * 1024

// RichTextViewer가 허용하는 태그/속성 — 에디터가 만들어내는 마크업과 맞춰 둔다
export const VIEWER_ALLOWED_TAGS = ['p', 'br', 'strong', 'b', 'em', 'i', 'u', 'span', 'mark', 'img']
export const VIEWER_ALLOWED_ATTR = ['style', 'src', 'alt', 'class']

export function isEmptyEditorHtml(html: string | null | undefined): boolean {
  const trimmed = (html || '').trim()
  return (
    !trimmed ||
    trimmed === '<p></p>' ||
    trimmed === '<p><br></p>' ||
    trimmed === '<p><br class="ProseMirror-trailingBreak"></p>'
  )
}

export interface EditorExtensionOptions {
  placeholder?: string
  /**
   * 이전 에디터(StarterKit 기본)로 작성된 본문의 제목/목록/인용/취소선/링크를
   * 스키마에 남겨 둔다. 툴바 버튼은 없지만, 기존 글을 열어 저장해도 서식이 사라지지 않는다.
   */
  preserveLegacyBlocks?: boolean
}

export function createEditorExtensions(options: EditorExtensionOptions = {}): Extensions {
  const { placeholder = '내용을 입력하세요', preserveLegacyBlocks = false } = options

  return [
    // TipTap v3 StarterKit에는 Underline이 포함되어 있어 별도 등록하지 않는다
    StarterKit.configure({
      codeBlock: false,
      horizontalRule: false,
      code: false,
      ...(preserveLegacyBlocks
        ? { link: { openOnClick: false } }
        : {
            heading: false,
            blockquote: false,
            bulletList: false,
            orderedList: false,
            listItem: false,
            // 뷰어 허용 태그에 없는 마크는 꺼 둔다
            link: false,
            strike: false,
          }),
    }),
    TextStyle,
    Color,
    FontSize,
    Highlight.configure({ multicolor: true }),
    Image.configure({
      inline: false,
      allowBase64: true,
    }),
    Placeholder.configure({ placeholder }),
  ]
}

export function readImageAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = () => reject(new Error('이미지를 읽지 못했습니다.'))
    reader.readAsDataURL(file)
  })
}
