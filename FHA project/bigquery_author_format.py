from google.cloud import bigquery
from google.oauth2 import service_account
import os

credentials = service_account.Credentials.from_service_account_file("/home/angelica_w/openalex-bigquery-65bc5c06079f.json")
#Construct BigQuery client object
client = bigquery.Client(credentials = credentials, project = "openalex-bigquery")

dataset_id = "openalex-bigquery.authors_2023_01_30"
tables = client.list_tables(dataset_id)
for table in tables:
    job_config = bigquery.QueryJobConfig(
        # Run at batch priority, which won't count toward concurrent rate limit.
        priority=bigquery.QueryPriority.BATCH,
        destination="openalex-bigquery.2023_01_30_authors." + table.table_id
    )
    table_id = "{}.{}.{}".format(table.project, table.dataset_id, table.table_id)
    # table_id = "openalex-bigquery.openalex_snapshot_2023_1_30.authors"
    sql = """
    SELECT 
        data0.id,
        name,
        name_alternative,
        orcid,
        works_count,
        TC,
        affiliation_name,
        affiliation_id,
        affiliation_ror,
        affiliation_country,
        affiliation_type,
        works_api_url,
        total_cite,
        concept_0,
        score_0,
        concept_1,
        score_1,
        concept_2,
        score_2,
        year_0,
        cited_0,
        year_1,
        cited_1,
        year_2,
        cited_2,
        year_3,
        cited_3,
        year_4,
        cited_4,
        year_5,
        cited_5,
        year_6,
        cited_6,
        year_7,
        cited_7,
        year_8,
        cited_8,
        year_9,
        cited_9,
        year_10,
        cited_10,
    FROM(
        SELECT * EXCEPT(total_yr_cite)
        FROM(
            SELECT * EXCEPT(yr_cite), SUM(yr_cite) as total_yr_cite
            FROM(
                SELECT
                    json_extract_scalar(author, '$.id') as id,
                    json_extract_scalar(author, '$.display_name') as name,
                    json_extract_scalar(author, '$.display_name_alternatives') as name_alternative,
                    json_extract_scalar(author, '$.ids.orcid') as orcid,
                    json_extract_scalar(author, '$.works_count') as works_count,
                    json_extract_scalar(author, '$.cited_by_count') as TC,
                    json_extract_scalar(author, '$.last_known_institution.display_name') as affiliation_name,
                    json_extract_scalar(author, '$.last_known_institution.id') as affiliation_id,
                    json_extract_scalar(author, '$.last_known_institution.ror') as affiliation_ror,
                    json_extract_scalar(author, '$.last_known_institution.country_code') as affiliation_country,
                    json_extract_scalar(author, '$.last_known_institution.type') as affiliation_type,
                    json_extract_scalar(author, '$.works_api_url') as works_api_url,

                    CAST(json_extract_scalar(p, '$.cited_by_count') AS int) as yr_cite,
                    CAST(json_extract_scalar(author, '$.cited_by_count') AS int) as total_cite

                FROM `%(table)s` 
                left join unnest(json_extract_array(author, '$.counts_by_year')) as p
            )t0
            GROUP BY id, name, name_alternative, orcid, works_count, TC, affiliation_name, affiliation_id, affiliation_ror, affiliation_country, affiliation_type, works_api_url, total_cite
        )t1
    )data0
    JOIN(
        WITH concept_data as(
            SELECT 
                id,
                ARRAY_AGG(c_name IGNORE NULLS) as concepts,
                ARRAY_AGG(c_score IGNORE NULLS) as scores
            FROM(
                SELECT * EXCEPT(arr) 
                FROM(
                    SELECT
                        id,
                        ARRAY_AGG(STRUCT(c_name, c_score) ORDER BY c_score DESC LIMIT 3) arr
                    FROM(
                        SELECT 
                            json_extract_scalar(author, '$.id') as id,
                            json_extract_scalar(c, '$.display_name') as c_name,
                            CAST(json_extract_scalar(c, '$.level') as int) as c_level,
                            CAST(json_extract_scalar(c, '$.score') as decimal) as c_score,

                        FROM `%(table)s` as file
                        left join unnest(json_extract_array(author, '$.x_concepts')) as c
                        WHERE CAST(json_extract_scalar(c, '$.level') as int) = 0 
                    ) c0
                    GROUP BY id
                    ), UNNEST(arr)
                )
            GROUP BY id
        )
        SELECT * 
        FROM (
            SELECT id, a, b, offset
            from concept_data, 
            unnest(concepts) a with offset
            join unnest(scores) b with offset
            using (offset)
        )
        pivot (min(a) as concept, min(b) as score for offset in (0, 1, 2))
    )AS data1
    ON data0.id = data1.id
    JOIN(
        WITH cite_data as(
            SELECT 
                id,
                ARRAY_AGG(year IGNORE NULLS) as years,
                ARRAY_AGG(cited IGNORE NULLS) as cited
            FROM(
                SELECT * EXCEPT(arr) 
                FROM(
                    SELECT
                        id,
                        ARRAY_AGG(STRUCT(year, cited)) arr
                    FROM(
                        SELECT 
                            json_extract_scalar(author, '$.id') as id,
                            json_extract_scalar(c, '$.year') as year,
                            CAST(json_extract_scalar(c, '$.cited_by_count') as int) as cited,
                        FROM `%(table)s` as file
                        left join unnest(json_extract_array(author, '$.counts_by_year')) as c
                    ) c0
                GROUP BY id
                ), UNNEST(arr)
            )
            GROUP BY id
        )
        SELECT * 
        FROM (
            SELECT id, a, b, offset
            FROM cite_data, 
            unnest(years) a with offset
            join unnest(cited) b with offset
            using (offset)
        )
        pivot (min(a) as year, min(b) as cited for offset in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10))
    )data2
    ON data0.id = data2.id
    """ % {'table' : table_id}

    # Start the query, passing in the extra configuration.
    query_job = client.query(sql, job_config=job_config)  # Make an API request.

    # Check on the progress by getting the job's updated state. Once the state
    # is `DONE`, the results are ready.
    # query_job = client.get_job(
    #     query_job.job_id, location=query_job.location
    # )  # Make an API request.
    # print(table_id)
    # print("Job {} is currently in state {}".format(query_job.job_id, query_job.state))
    query_job.result()
    print("Query results loaded to the table{}".format(table_id))