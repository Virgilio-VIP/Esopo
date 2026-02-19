# Esopo Knowledge Base: Database Schema

## Overview
This document serves as the data dictionary for the Esopo project, mapping SQL Server tables and fields to their business meanings.

## Standards
- **Date Format (Internal)**: SQL Server uses `MM/DD/YYYY`.
- **Date Format (UI)**: Dashboards MUST display as `DD/MM/YYYY`.
- **Active Animal Logic (PROD STANDARD)**:
    An animal is considered **ACTIVE** only if its origin is not External and its category is not flagged as Morto or Vendido.
    **SQL Filter Pattern**:
    ```sql
    WHERE cad_fichario.Origem <> 'E' 
    AND cad_fichario.cod_categoria NOT IN (
        SELECT cod_categoria FROM Tab_categoria WHERE morto = 'S' OR vendido = 'S'
    )
    ```
    *Note: 'S' indicates 'Sim' (Yes/Active Flag).*

## Tables

### `cad_fichario` (Master record)
Central animal registry.

#### Master Record Fields
- `cod_fazenda`: Foreign key to `Tab_Fazenda`. **Used for primary filtering.**
- `cod_animal`: Internal Database ID (Single unique identifier).
- `id_animal`: Visual identification (Ear tag).
- `nome`: Name (Stud Bulls).
- `transponder`: Electronic chip number.
- `sisbov`: Official Brazilian traceability ID.
- `cod_mae`, `cod_pai`: Parents' IDs.
- `dt_nascimento`: Date of birth (**Activation by birth**).
- `dt_compra`: Primary purchase date (The very first time the animal was bought from an external source).
- `dt_entrada`: Arrival date at the **current** farm (`cod_fazenda`).
    - *Note: This date is updated on internal transfers between system farms.*
- `sexo`: Gender.
- `cod_raca`: Foreign key to `Tab_raca`.
- `origem`: Source/Status.
    - `N`: Nascido (Born).
    - `C`: Comprado (Purchased).
    - `E`: Externo (Sêmen/Not in herd) -> **INACTIVE**.
- `tipo`: Production type (Meat vs. Milk).

#### Grouping & Classification Fields
*These fields are used to group animals for management and reporting:*
- `cod_categoria`: Foreign key to `Tab_categoria`.
- `cod_extrato`: Foreign key to `Tab_extrato`. (Used for animal grouping similar to Category).
- `cod_lote`: Foreign key to `Tab_lote`.
- `cod_local`: Foreign key to `Tab_local`.

---

## Business Rules: Ingress & Transfers

### 🌍 External Purchase (Ingress)
- When an animal is bought from a source NOT in `Tab_fazenda`:
  - A record is created in **`cad_compra`**.
  - **`dt_compra`** and **`dt_entrada`** in `cad_fichario` are typically identical at this point.

### 🚜 Internal Transfer (Movement)
- When an animal moves between farms already registered in **`Tab_fazenda`**:
  - A record is created in **`cad_movimento`** with **`tipo = 'FAZENDA'`**.
  - **NO** records are created in `cad_venda` (at origin) or `cad_compra` (at destination).
  - In **`cad_fichario`**:
    - **`cod_fazenda`** is updated to the new location.
    - **`dt_entrada`** is updated to the transfer date.
    - **`dt_compra`** remains unchanged (preserving the original entry date to the system).

---

## Transactional Tables (Ingress / Egress / Movement)

### 📤 Egress (Exit / Inactivation)
Tables representing the removal of animals from the active herd.

#### `cad_morte` (Death Registry)
- `cod_animal`: Unique FK to `cad_fichario`.
- `data`: Date of death (**Inactivation by death**).
- `cod_causa_mortis`: FK to `Tab_causa_mortis`.

#### `cad_venda` (Sale Registry)
- `cod_animal`: Unique FK to `cad_fichario`.
- `data`: Date of sale (**Inactivation by sale**).
- `cod_criador`: FK to `Tab_criador` (Indicates the buyer).

### 📥 Ingress (Entry / Activation)
Tables representing the addition of animals to the active herd.

#### `cad_compra` (Purchase Registry)
- `cod_animal`: Unique FK to `cad_fichario`.
- `data`: Date of purchase (**Activation by purchase**).
- `cod_criador`: FK to `Tab_criador` (Source/Seller).
- `cod_criador_destino`: FK to `Tab_criador` (Target).

### 🔄 Historical Tracking
#### `cad_movimento` (Movement History)
Records all changes in the animal's status or location over time.
- `sequencial`: Database sequence (Primary Key).
- `cod_fazenda`: FK to `Tab_fazenda` (Where the animal was when the move occurred).
- `cod_animal`: Unique FK to `cad_fichario`.
- `data`: Date of the movement.
- `tipo`: Type of change. Values include:
    - `LOCAL`: Change in `cod_local`.
    - `CATEGORIA`: Change in `cod_categoria`.
    - `LOTE`: Change in `cod_lote`.
    - `REBANHO`: Change in `cod_rebanho`.
    - `FAZENDA`: Change in `cod_fazenda`.

---

### `cad_pesagem_corte` (Weight records)
- `cod_animal`: Foreign key to `cad_fichario`.
- `data`: Date of weighing.
- `peso`: Weight in Kg.
- `GPM`: Monthly Weight Gain (Ganho por Mês).
- `GPD`: Daily Weight Gain (Ganho por Dia).

---

### Accessory Tables (Master Data)

- **`Tab_fazenda`**: `cod_fazenda`, `descricao`.
- **`Tab_categoria`**: 
    - `cod_categoria`, `descricao`.
    - `Fase`: Physiological stage.
    - `unidade_animal`: Physiological weight factor (e.g., 1.0 = Adult cow, 0.25-0.40 = Calf).
    - `MORTO`: Flag ('S' = Inactive).
    - `VENDIDO`: Flag ('S' = Inactive).
- **`Tab_extrato`**: `cod_extrato`, `descricao` (Grouping).
- **`Tab_lote`**: `cod_lote`, `descricao` (Grouping).
- **`Tab_local`**: `cod_local`, `descricao` (Grouping).
- **`Tab_raca`**: `cod_raca`, `descricao`.
- **`Tab_criador`**: `cod_criador`, `descricao`.
- **`Tab_causa_mortis`**: `cod_causa_mortis`, `descricao`.

---
*This file is updated as new knowledge is provided by the USER.*
