export function tarihSaatFormatla(deger) {
  if (deger === null || deger === undefined || deger === '') return 'Veri yok';

  const normalDeger = typeof deger === 'string' && /^\d+$/.test(deger)
    ? Number(deger)
    : deger;
  const tarih = new Date(normalDeger);

  if (Number.isNaN(tarih.getTime())) return 'Veri yok';

  return new Intl.DateTimeFormat('tr-TR', {
    dateStyle: 'short',
    timeStyle: 'medium',
  }).format(tarih);
}

