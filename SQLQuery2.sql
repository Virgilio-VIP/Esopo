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