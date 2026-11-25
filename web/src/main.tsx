import { Component, StrictMode, type ReactNode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import App from './App';

class ErrorBoundary extends Component<{ children: ReactNode }, { err: string }> {
  state = { err: '' };
  static getDerivedStateFromError(error: Error) {
    return { err: error?.message || '页面渲染异常' };
  }
  render() {
    if (this.state.err) {
      return (
        <div className="min-h-screen flex items-center justify-center p-6 bg-[#F3F6FA]">
          <div className="max-w-md w-full bg-white border border-red-200 rounded-2xl p-6 shadow-md space-y-3">
            <h1 className="text-base font-bold text-red-700">页面渲染遇到异常</h1>
            <p className="text-xs text-slate-600 font-mono break-all">{this.state.err}</p>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="px-4 py-2 rounded-xl text-xs font-semibold bg-[#0A192F] text-white cursor-pointer"
            >
              重新加载页面
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>
);
