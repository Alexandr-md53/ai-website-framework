Frozen Contracts — C4 .. C16.5
Slice	Contract	Implementation	Tests	Tag / Commit	Status
C4	scaffold crud template filesystem-only, manifest.json only	cli scaffold_crud, validate_scaffold, -crud suffix	test_c4_freeze, test_cli_new_*	phase-10.2-c4-frozen 70af32e 430	FROZEN
C5.1	api read-only filesystem-only registry ProductInfo, list_products, get_product	ai_framework/api registry	test_c5_registry	phase-10.2-c5.1-frozen 87a53e1 433	FROZEN
C5.2	registry enrichment pyproject_name/version/requires_python + lru_cache	registry enrichment	test_c5_2_enrichment	phase-10.2-c5.2-frozen 93ea5a6 435	FROZEN
C5.3	cli read-only hooks product list/showcase list/info via list_products/get_product	cli	test_c5_3_cli	phase-10.2-c5.3-frozen 10b1388 439	FROZEN
C5.4	cli version + product info alias + --json	cli	test_c5_4_cli	phase-10.2-c5.4-frozen 63b1082 444	FROZEN
C5.5	api inspect_project export + cli inspect <path> [--json] filesystem-only	api inspect	test_c5_5_inspect	phase-10.2-c5.5-frozen efbc1f4 447	FROZEN
C6.1	fastapi factory create_app(registry=None) → FastAPI wiring over frozen EndpointRegistry/Router/APIAdapter	api/app_factory	test_c6_1_fastapi_factory	phase-11-c6.1-frozen 04e0f18 449	FROZEN
C6.2	extended wiring middlewares+health+lifespan passthrough over frozen Router/Adapter	wiring	test_c6_2_fastapi_wiring	phase-11-c6.2-frozen 13dbe66 454	FROZEN
C7.2	application boundary freeze (pipeline+adapter+repo+use_cases)	application	test_c7_2_application_contract	phase-11-c7.2-frozen c066337 464	FROZEN
C7.3	product execution boundary freeze CRUDContext/CRUDResult/CRUDError/PersistenceProtocol/UniversalEngine	crud/init	test_c7_3_product_execution	phase-11-c7.3-frozen b397003 477	FROZEN
C8.1	api->application wiring contract tests (8 tests)	wiring contract	test_c8_1_api_application_wiring	1a72ce3 485	FROZEN
C8.2	EndpointPipelineAdapter dto_factory+context_factory+pipeline.execute passthrough new file only	api/adapter	test_c8_2_pipeline_adapter_impl	phase-11-c8.2-frozen a2b460d 489	FROZEN
C9.1	fastapi+pipeline wiring contract (6) canonical crud.contracts import	wiring	test_c9_1_fastapi_pipeline_wiring	phase-11-c9.1-frozen 3507fa9 495	FROZEN
C9.2	endpoint pipeline registration helper 5 tests new file only	helper	test_c9_2_endpoint_pipeline_registration	phase-11-c9.2-frozen 23a0cce 500	FROZEN
C9.3	full fastapi wiring via helper 4 tests integration proof	helper	test_c9_3_fastapi_product_wiring	phase-11-c9.3-frozen 7de3614 504	FROZEN
C10.1	product assembly factory metadata->C9.2->C6 no fs scan new file only	ProductFactory	test_c10_1_product_factory	phase-11-c10.1-frozen a5c4ca0 510	FROZEN
C12.1	cafe showcase via product factory	showcases/cafe	test_c12_1_cafe_showcase_via_factory	phase-12-c12.1-frozen c579197	FROZEN
C12.2	status transition DRAFT->ACTIVE->ARCHIVED via product factory	cafe status	test_c12_2_cafe_status_transition	phase-12-c12.2-frozen d0ff074	FROZEN
C12.3	lawyer submit_consultation_request M2M validation via product factory	lawyer	test_c12_3_lawyer_submit_request	phase-12-c12.3-frozen 9249dff	FROZEN
C12.4	lawyer consultation list RBAC	lawyer RBAC	test_c12_4_lawyer_list_rbac	phase-12-c12.4-frozen b49c3eb	FROZEN
C13.1	plant_nursery catalog via ProductFactory	plant_nursery	test_c13_1_plant_nursery_catalog	phase-13-c13.1-frozen 4f7daf4 524	FROZEN
C13.2	category hierarchy validation via ValidationEngine	category validation	test_c13_2_category_hierarchy_api	phase-13-c13.2-frozen 1e52432 528	FROZEN
C13.3	MoveCategory via ValidationEngine	category move	test_c13_3_category_move_api	phase-13-c13.3-frozen 37a1209 533	FROZEN
C13.4	Category->Plants aggregation with descendants BFS	aggregation	test_c13_4_category_plants_api	phase-13-c13.4-frozen dfb64d2 538	FROZEN
C14.1	Plant gallery POST /plants/{id}/images limit 5 + main_image auto	gallery	test_c14_1_plant_gallery_api	phase-14-c14.1-frozen 6e103bb 543	FROZEN
C14.2	GET /plants/{id}/images gallery read + count	gallery	test_c14_2_plant_gallery_get_api	phase-14-c14.2-frozen 48e1cbd 546	FROZEN
C14.3	DELETE /plants/{id}/images/{image_id} main promotion	gallery delete	test_c14_3_plant_gallery_delete_api	phase-14-c14.3-frozen d7b53af 550	FROZEN
C14.4	VOLUME threshold >=10 fix	pricing	test_c14_4_volume_threshold_api	phase-14-c14.4-frozen c4fe436 554	FROZEN
C15.1	Lawyer consultation status lifecycle PENDING->APPROVED	REJECTED->COMPLETED RBAC	lawyer status	test_c15_1_consultation_status_api	phase-15-c15.1-frozen 3d3b2a8 559
C16.1	Plant stock PATCH /plants/{id}/stock quantity + is_available	plant_nursery	test_c16_1_plant_stock_api	phase-16-c16.1-frozen a67b4ae 564	FROZEN
C16.2	GET /plants?available filter true/false + fix empty list without min_temp	filter	test_c16_2_plant_available_filter_api	phase-16-c16.2-frozen cce1fc7 568	FROZEN
C16.3	stock fields in POST /plants and GET /categories/{id}/plants	responses	test_c16_3_plant_stock_in_responses_api	phase-16-c16.3-frozen b447d62 571	FROZEN
C16.4	quote stock validation OUT_OF_STOCK/INSUFFICIENT_STOCK - 400	quote validation	test_c16_4_quote_stock_validation_api	phase-16-c16.4-frozen f59a162 575	FROZEN
C16.5	quote decrement stock logic + ValueError→400 mapping, PipelineContext frozen	quote decrement	test_c16_5_quote_decrement_api	phase-16-c16.5-frozen e3933e9 HEAD b3c2c2d	FROZEN
