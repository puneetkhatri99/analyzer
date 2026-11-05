import React from "react";
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Tooltip } from "chart.js";
import { Bar } from "react-chartjs-2";
import { money, moneyShort } from "../format.js";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip);

const INK_MUTED = "#6b6b6b";
const GRID = "#efeeec";
const BAR = "#b9b8b4";
const HUE = "#1d5fbf";

// Draws the median as a 2px line in the screen's one hue, labelled at the top.
const medianLine = {
  id: "medianLine",
  afterDatasetsDraw(chart, _args, opts) {
    if (opts.value == null) return;
    const x = chart.scales.x;
    const i = Math.min(Math.floor(opts.value / opts.bin), x.ticks.length - 1);
    const width = x.ticks.length > 1 ? x.getPixelForValue(1) - x.getPixelForValue(0) : x.width;
    const px = x.getPixelForValue(i) + ((opts.value % opts.bin) / opts.bin - 0.5) * width;
    const { top, bottom } = chart.chartArea;
    const ctx = chart.ctx;
    ctx.save();
    ctx.fillStyle = HUE;
    ctx.fillRect(Math.round(px) - 1, top + 18, 2, bottom - top - 18);
    ctx.font = "500 12px Geist, Inter, system-ui, sans-serif";
    ctx.textBaseline = "top";
    const label = `Median ${money(opts.value)}`;
    const w = ctx.measureText(label).width;
    const tx = px + 6 + w > chart.chartArea.right ? px - 6 - w : px + 6;
    ctx.fillText(label, tx, top);
    ctx.restore();
  },
};

export default function PayDistribution({ histogram, bin, cap, median }) {
  const labels = histogram.map((b) => (b.from >= cap ? `${moneyShort(cap)}+` : moneyShort(b.from)));
  const data = {
    labels,
    datasets: [{ data: histogram.map((b) => b.count), backgroundColor: BAR, hoverBackgroundColor: "#8a8a8a", borderRadius: 0, categoryPercentage: 0.92, barPercentage: 1 }],
  };
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 200 },
    layout: { padding: { top: 4 } },
    plugins: {
      legend: { display: false },
      medianLine: { value: median, bin },
      tooltip: {
        displayColors: false,
        backgroundColor: "#141414",
        padding: 8,
        titleFont: { family: "Geist", weight: "500" },
        bodyFont: { family: "Geist" },
        callbacks: {
          title: (items) => {
            const from = histogram[items[0].dataIndex].from;
            return from >= cap ? `${money(cap)} or more` : `${money(from)}–${money(from + bin - 1)}`;
          },
          label: (item) => `${item.raw} posting${item.raw === 1 ? "" : "s"}`,
        },
      },
    },
    scales: {
      x: {
        grid: { display: false },
        border: { color: "#d4d4d4" },
        ticks: {
          color: INK_MUTED, font: { family: "Geist", size: 12 }, maxRotation: 0, autoSkip: false,
          // every 2nd bin on desktop, every 4th on narrow charts, so labels never collide
          callback: function (_v, i) {
            const every = this.chart.width < 480 ? 4 : 2;
            if (i === labels.length - 1) return labels[i];
            return i % every === 0 && labels.length - 1 - i >= every / 2 ? labels[i] : "";
          },
        },
      },
      y: {
        beginAtZero: true,
        grid: { color: GRID },
        border: { display: false },
        ticks: { color: INK_MUTED, font: { family: "Geist", size: 12 }, precision: 0, maxTicksLimit: 5 },
      },
    },
  };

  return (
    <div className="chart-box" role="img" aria-label={`Histogram of annual pay in $${bin / 1000}k bands; median ${money(median)}.`}>
      <Bar data={data} options={options} plugins={[medianLine]} />
    </div>
  );
}
