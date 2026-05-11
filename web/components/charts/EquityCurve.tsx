"use client";

/**
 * EquityCurve — area chart of daily equity points.
 *
 * Uses Lightweight Charts (official TradingView v5). The chart instance
 * lives in a ref so we can imperatively update the series when props
 * change without remounting the canvas.
 */

import { useEffect, useRef } from "react";
import {
  AreaSeries,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type Time,
} from "lightweight-charts";
import type { EquityPoint } from "@/lib/api";

interface Props {
  points: EquityPoint[];
  height?: number;
}

export function EquityCurve({ points, height = 280 }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Area"> | null>(null);

  // Create the chart once
  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      height,
      autoSize: true,
      layout: {
        background: { color: "transparent" },
        textColor: "rgb(180 180 195)",
      },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.04)" },
        horzLines: { color: "rgba(255,255,255,0.04)" },
      },
      timeScale: { borderColor: "rgba(255,255,255,0.1)", timeVisible: false },
      rightPriceScale: { borderColor: "rgba(255,255,255,0.1)" },
      crosshair: { mode: 0 },
    });
    const series = chart.addSeries(AreaSeries, {
      topColor: "rgba(34, 197, 94, 0.35)",
      bottomColor: "rgba(34, 197, 94, 0.02)",
      lineColor: "rgb(34, 197, 94)",
      lineWidth: 2,
      priceLineVisible: false,
    });
    chartRef.current = chart;
    seriesRef.current = series;

    return () => {
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, [height]);

  // Update data when points change
  useEffect(() => {
    if (!seriesRef.current) return;
    const data = points.map((p) => ({
      time: p.date as Time,
      value: p.equity,
    }));
    seriesRef.current.setData(data);
    chartRef.current?.timeScale().fitContent();
  }, [points]);

  if (points.length === 0) {
    return (
      <div
        className="flex items-center justify-center rounded-md border border-dashed border-border text-sm text-muted-foreground"
        style={{ height }}
      >
        No equity points yet. Close a trade to populate.
      </div>
    );
  }

  return <div ref={containerRef} className="w-full" style={{ height }} />;
}
