use Vipper_FRS

WITH UltimaPesagem AS ( 
	SELECT cod_animal, peso, data, GPM, GPD, ROW_NUMBER() OVER (PARTITION BY cod_animal ORDER BY data DESC) as rn FROM cad_pesagem_corte ) 
SELECT t.descricao as Categoria, COUNT(c.cod_animal) as [Qtd Animais], AVG(DATEDIFF(month, c.dt_nascimento, GETDATE())) as [Idade Média (Meses)]
, AVG(up.peso) as [Peso Médio (Kg)], AVG(up.GPM) as [GMD Médio], AVG(up.GPD) as [GPD Médio], AVG(DATEDIFF(day, up.data, GETDATE())) as [Idade Pesagem (Dias)]
, COUNT(up.peso) as [Qtd Pesagens] 
FROM cad_fichario c JOIN Tab_categoria t ON c.cod_categoria = t.cod_categoria 
LEFT JOIN UltimaPesagem up ON c.cod_animal = up.cod_animal AND up.rn = 1 
WHERE c.Origem <> 'E' 
AND c.cod_categoria NOT IN ( SELECT cod_categoria FROM Tab_categoria WHERE morto = 'S' OR vendido = 'S' ) 
AND c.cod_fazenda IN ('1', '2', '3', '4', '5') 
GROUP BY t.descricao
ORDER BY [Qtd Animais] DESC 

select * from cad_compra
select * from cad_movimento where cod_animal = 3
select * from cad_fichario where cod_animal = 3
select * from cad_venda

select * from cad_fichario 
where cod_fazenda = 5
 and cod_categoria not in ('VD','MT')
 and origem <> 'E'
 3.202


 SELECT FORMAT(data, 'yyyy-MM-01') as Mes, 'COMPRA' as Tipo, COUNT(*) as Qtd, SUM(t.unidade_animal) as UA 
 FROM cad_compra cc JOIN cad_fichario c ON cc.cod_animal = c.cod_animal JOIN Tab_categoria t ON c.cod_categoria = t.cod_categoria 
 WHERE c.cod_fazenda IN (1) 
 GROUP BY FORMAT(data, 'yyyy-MM-01') 
 UNION ALL 
 SELECT FORMAT(dt_nascimento, 'yyyy-MM-01') as Mes, 'NASCIMENTO' as Tipo, COUNT(*) as Qtd, SUM(t.unidade_animal) as UA 
 FROM cad_fichario c JOIN Tab_categoria t ON c.cod_categoria = t.cod_categoria 
 WHERE c.cod_fazenda IN (1) 
 GROUP BY FORMAT(dt_nascimento, 'yyyy-MM-01')
 
 
 
 SELECT FORMAT(data, 'yyyy-MM-01') as Mes, 'MORTE' as Tipo, COUNT(*) as Qtd, SUM(t.unidade_animal) as UA 
 FROM cad_morte cm JOIN cad_fichario c ON cm.cod_animal = c.cod_animal JOIN Tab_categoria t ON c.cod_categoria = t.cod_categoria 
 WHERE c.cod_fazenda IN (1) 
 GROUP BY FORMAT(data, 'yyyy-MM-01') 
 UNION ALL 
 SELECT FORMAT(data, 'yyyy-MM-01') as Mes, 'VENDA' as Tipo, COUNT(*) as Qtd, SUM(t.unidade_animal) as UA 
 FROM cad_venda cv JOIN cad_fichario c ON cv.cod_animal = c.cod_animal JOIN Tab_categoria t ON c.cod_categoria = t.cod_categoria 
 WHERE c.cod_fazenda IN (1) 
 GROUP BY FORMAT(data, 'yyyy-MM-01')



 SELECT DISTINCT tc.cod_criador, tc.descricao 
 FROM cad_venda cv JOIN Tab_criador tc ON cv.cod_criador = tc.cod_criador JOIN cad_fichario cf ON cv.cod_animal = cf.cod_animal 
 WHERE cf.cod_fazenda IN (1) 
 AND cv.data >= DATEADD(month, -{periodo_meses}, GETDATE())

 SELECT DISTINCT tc.cod_criador, tc.descricao, cv.data, DATEADD(month, -1, GETDATE()) AS PER
 FROM cad_venda cv JOIN Tab_criador tc ON cv.cod_criador = tc.cod_criador JOIN cad_fichario cf ON cv.cod_animal = cf.cod_animal 
 WHERE cf.cod_fazenda IN (1) 
 AND cv.data >= DATEADD(month, -1, GETDATE())

 
 WITH Entry AS (
      SELECT cc.cod_animal, cc.data as dte, cc.peso as pe, tc.descricao as forn, 
      'COMPRA: ' + CAST(cc.data AS VARCHAR) + ' - ' + tc.descricao as grp
      FROM cad_compra cc JOIN Tab_criador tc ON cc.cod_criador = tc.cod_criador
),
      Sale AS (
      SELECT cv.cod_animal, cv.data as dtv, cv.peso as pev_orig, tc.descricao as comp, cv.cod_criador_origem
      FROM cad_venda cv JOIN Tab_criador tc ON cv.cod_criador = tc.cod_criador
      WHERE cv.cod_criador IN ('MINE') AND cv.data >= DATEADD(month, -6, GETDATE())
),
      LW AS (
      SELECT cod_animal, peso, ROW_NUMBER() OVER (PARTITION BY cod_animal ORDER BY data DESC) as rn
      FROM cad_pesagem_corte
)
      SELECT cf.id_animal, cf.origem, s.comp, s.dtv, 
      ISNULL(lw.peso, s.pev_orig) as pv,
      CASE WHEN cf.origem = 'N' THEN cf.dt_nascimento ELSE cf.dt_compra END as di,
      DATEDIFF(day, CASE WHEN cf.origem = 'N' THEN cf.dt_nascimento ELSE cf.dt_compra END, s.dtv) as td,
      CASE WHEN cf.origem = 'N' THEN 'NASCIMENTO: ' + CAST(FORMAT(cf.dt_nascimento, 'MM/yyyy') AS VARCHAR) 
	  ELSE e.grp END as og,
      ISNULL(e.pe, 40.0) as pi
      FROM cad_fichario cf
      JOIN Sale s ON cf.cod_animal = s.cod_animal
      LEFT JOIN Entry e ON cf.cod_animal = e.cod_animal
      LEFT JOIN LW lw ON cf.cod_animal = lw.cod_animal AND lw.rn = 1
      WHERE cf.cod_fazenda IN (1)
