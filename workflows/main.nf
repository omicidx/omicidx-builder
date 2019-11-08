entities = Channel.from( "study", "experiment", "run", "sample")
// entities = Channel.from("run")

process es_index {
    tag "$entity"
    
    input:
    val entity from entities

    shell:
    """
    omicidx_builder sra sra-gcs-to-elasticsearch -e $entity 
    """

}
