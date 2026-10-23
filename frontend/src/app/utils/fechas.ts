const ZONA = 'America/Bogota';

/** Fecha y hora del servidor siempre en hora de Bogotá. */
export function fechaHoraBogota(valor: string): string {
  return (
    new Intl.DateTimeFormat('es-CO', {
      timeZone: ZONA,
      dateStyle: 'medium',
      timeStyle: 'medium',
    }).format(new Date(valor)) + ' (Bogotá)'
  );
}

/** Fecha sin hora (AAAA-MM-DD) en formato local para mostrar. */
export function fechaBogota(iso: string): string {
  const [anio, mes, dia] = iso.split('-').map(Number);
  if (!anio || !mes || !dia) return iso;
  return new Date(anio, mes - 1, dia).toLocaleDateString('es-CO', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
}

/** Fecha de hoy en Bogotá como AAAA-MM-DD, para comparar vencimientos. */
export function hoyBogota(): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: ZONA,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date());
}
