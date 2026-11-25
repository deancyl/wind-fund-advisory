import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

interface EChartBoxProps {
  option: echarts.EChartsCoreOption;
  height?: number;
  className?: string;
}

/**
 * 通用自适应 ECharts 容器组件。
 * 统一托管实例化、ResizeObserver 响应式缩放与销毁，
 * 未来扩展 K 线图模块（Candlestick + Volume + MA/MACD）可直接复用本组件。
 */
export function EChartBox({ option, height = 320, className = '' }: EChartBoxProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const chart = echarts.init(el, undefined, { renderer: 'canvas' });
    chartRef.current = chart;

    const ro = new ResizeObserver(() => {
      chart.resize();
    });
    ro.observe(el);

    return () => {
      ro.disconnect();
      chart.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (chartRef.current && option) {
      chartRef.current.setOption(option, { notMerge: true });
    }
  }, [option]);

  return <div ref={containerRef} style={{ height: `${height}px` }} className={`w-full ${className}`} />;
}
