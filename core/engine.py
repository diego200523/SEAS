"""Reglas RN01-RN10. Funciones puras; no dependen de HTTP ni de la base de datos."""
from fractions import Fraction

MATRIX = [[1,1,2,2],[1,2,2,3],[2,2,3,3],[2,3,3,4]]
CATEGORIES = ('Fortaleza','Oportunidad','Debilidad','Amenaza')

def level(value):
    if type(value) is not int or not 1 <= value <= 4:
        raise ValueError('Cada valoración debe ser un entero entre 1 y 4.')
    return value

def relative(decisor, suggested, matrix):
    return matrix[level(decisor)-1][level(suggested)-1]

def calculate(snapshot, data):
    catalog, matrix = snapshot['catalog'], snapshot['matrix']
    if not catalog:
        raise ValueError('No existen factores activos con subfactores.')
    results = []
    for factor in catalog:
        importance = data['importance'].get(factor['id'])
        ir = relative(importance, factor['is'], matrix)
        if ir == 1:
            continue
        impact = data.get('support') if factor['impact'] == 'AMBOS' else factor['impact']
        if impact not in ('INTERNO','EXTERNO'):
            raise ValueError('Seleccione el impacto del soporte.')
        values = [level(data['answers'].get(s['id'])) for s in factor['subs']]
        if not values:
            raise ValueError('El factor no tiene subfactores activos.')
        mean = Fraction(sum(values),len(values))
        category = ('Fortaleza' if impact=='INTERNO' else 'Oportunidad') if mean>=3 else ('Debilidad' if impact=='INTERNO' else 'Amenaza')
        results.append({**factor,'ir':ir,'pm':float(mean),'impact':impact,'foda':category})
    if not results:
        raise ValueError('No hay factores relevantes. Revise las importancias.')
    critical = [f for f in results if f['ir']>=3]
    bad = [f for f in critical if f['foda'] in ('Debilidad','Amenaza')]
    text = 'Adoptar' if not bad else 'Adoptar con condiciones' if 2*len(bad)<=len(critical) else 'No adoptar por ahora'
    return results, {'text':text,'bad':len(bad),'total':len(critical),'tone':'green' if not bad else 'amber' if 2*len(bad)<=len(critical) else 'red','rule':'RN09: regla operativa del proyecto SEAS; no es una conclusión automática de la tesis.'}
