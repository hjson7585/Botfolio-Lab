// Vite에서 설정을 만들 때 사용하는 함수 가져오기
import { defineConfig } from 'vite'

// React 프로젝트가 Vite에서 잘 동작하도록 도와주는 플러그인 가져오기
import react from '@vitejs/plugin-react'

// Tailwind CSS를 Vite에 연결해 주는 플러그인 가져오기
import tailwindcss from '@tailwindcss/vite'

// 이 파일의 기본 설정을 내보냄
export default defineConfig({
  // Vite에서 사용할 플러그인 목록
  plugins: [
    // React 문법(JSX 등)을 사용할 수 있게 해줌
    react(),

    // Tailwind CSS가 작동하도록 연결해 줌
    tailwindcss(),
  ],
})
