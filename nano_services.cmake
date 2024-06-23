list(APPEND CMAKE_MODULE_PATH ${ZEPHYR_BASE}/modules/nanopb)
include(nanopb)

set(NANOPB_OPTIONS "--c-style")

set(CMAKE_NANO_SERVICE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/zns")

include_directories(${CMAKE_NANO_SERVICE_MODULE_PATH})
include_directories(${CMAKE_CURRENT_BINARY_DIR}/include)
include_directories(${CMAKE_CURRENT_BINARY_DIR}/nano_services)
# include_directories(${CMAKE_CURRENT_BINARY_DIR}/src/nano_services)

function(nano_service_include_proto target)
  foreach(service_proto_file IN LISTS ARGN)
    message(WARNING ${service_proto_file})
    zephyr_nanopb_sources(${target} ${service_proto_file})
  endforeach()
endfunction()

function(nano_service_register target)
  foreach(service_proto_file IN LISTS ARGN)
    message(WARNING ${service_proto_file})
    zephyr_nanopb_sources(${target}
                          ${CMAKE_CURRENT_SOURCE_DIR}/${service_proto_file})
    get_filename_component(service_name ${service_proto_file} NAME_WE)
    set(service ${service_name})
    string(TOUPPER ${service} SERVICE_UPPER)
    configure_file(${CMAKE_NANO_SERVICE_MODULE_PATH}/nano_service_template.c.in
                   nano_services/${service}.c @ONLY)
    configure_file(${CMAKE_NANO_SERVICE_MODULE_PATH}/nano_service_template.h.in
                   nano_services/${service}.h @ONLY)
    target_sources(
      ${target} PRIVATE ${CMAKE_CURRENT_BINARY_DIR}/nano_services/${service}.c)
  endforeach()
endfunction()
