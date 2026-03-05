const COLOR_MAP = {
  green:  { bg: 'bg-green-50',  text: 'text-green-700',  badge: 'bg-green-100 text-green-700'  },
  red:    { bg: 'bg-red-50',    text: 'text-red-700',    badge: 'bg-red-100 text-red-600'      },
  blue:   { bg: 'bg-blue-50',   text: 'text-blue-700',   badge: 'bg-blue-100 text-blue-700'    },
  orange: { bg: 'bg-orange-50', text: 'text-orange-700', badge: 'bg-orange-100 text-orange-700'},
  yellow: { bg: 'bg-yellow-50', text: 'text-yellow-700', badge: 'bg-yellow-100 text-yellow-700'},
  purple: { bg: 'bg-purple-50', text: 'text-purple-700', badge: 'bg-purple-100 text-purple-700'},
  gray:   { bg: 'bg-gray-50',   text: 'text-gray-700',   badge: 'bg-gray-100 text-gray-600'    },
};

function KpiCard({ card }) {
  const c = COLOR_MAP[card.color] || COLOR_MAP.gray;
  return (
    <div className={`rounded-xl p-4 ${c.bg} flex flex-col gap-1 flex-1 min-w-0`}>
      <p className="text-xs font-medium text-gray-500 truncate">{card.title}</p>
      <p className={`text-2xl font-bold ${c.text} truncate`}>{card.value}</p>
      {card.change != null && (
        <p className={`text-xs font-medium ${card.change >= 0 ? 'text-red-500' : 'text-green-600'}`}>
          {card.change >= 0 ? '▲' : '▼'} {Math.abs(card.change)}% {card.change_label || ''}
        </p>
      )}
    </div>
  );
}

export default function KpiCardWidget({ data }) {
  const cards = data?.cards || [];
  if (!cards.length) {
    return <div className="flex items-center justify-center h-full text-gray-400 text-sm">No data</div>;
  }
  return (
    <div className="flex flex-wrap gap-3 h-full content-start">
      {cards.map(card => <KpiCard key={card.id} card={card} />)}
    </div>
  );
}
