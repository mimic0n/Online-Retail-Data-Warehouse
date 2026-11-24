// Create server/database parameters in Power Query; duplicate for each table.
let
    Source = PostgreSQL.Database("localhost:5432", "retail_dwh"),
    FactSales = Source{[Schema="dw",Item="fact_sales"]}[Data]
in
    FactSales
