export function canliOzetiOlustur(guvenlikOlaylari = [], sonDegerlendirmeOlayi = null) {
  const sonOlay = guvenlikOlaylari[0] || null;
  return {
    gosterilenOlay: guvenlikOlaylari.length,
    sonOlayZamani: sonOlay?.event_timestamp ?? sonOlay?.received_at ?? null,
    sonKarar: sonDegerlendirmeOlayi?.assessment?.decision || 'Değerlendirme yok',
  };
}
