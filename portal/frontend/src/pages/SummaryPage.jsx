export default function SummaryPage() {
  return (
    <div className="rounded-3xl bg-white/5 p-5 ring-1 ring-white/10">
      <h1 className="text-lg font-semibold">Сводка</h1>
      <p className="mt-1 text-sm text-slate-400">
        Здесь будет гистограмма по дням (active/away/afk/productive) и отметки серых дней
        (Праздник/Выходной), связанные с календарём «Отсутствие».
      </p>
    </div>
  )
}
