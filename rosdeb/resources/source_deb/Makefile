export ROS_DISTRO_DIR_FINAL=/opt/ros/${ROS_DISTRO_NAME}
export ROS_DISTRO_DIR=${ROS_DESTDIR}${ROS_DISTRO_DIR_FINAL}
export ROS_STACK_DIR=${ROS_DISTRO_DIR}/stacks
export ROS_STACK_DIR_FINAL=${ROS_DISTRO_DIR_FINAL}/stacks

${ROS_DISTRO_DIR}/${ROS_STACK_NAME}: ${ROS_STACK_NAME}-${ROS_STACK_VERSION}.md5 ../${ROS_STACK_NAME}-${ROS_STACK_VERSION}.tar.bz2
	md5sum -c ${ROS_STACK_NAME}-${ROS_STACK_VERSION}.md5 && (mkdir -p ${ROS_STACK_DIR} && cd ${ROS_STACK_DIR} && bunzip2 $(CURDIR)/../${ROS_STACK_NAME}-${ROS_STACK_VERSION}.tar.bz2 -c | tar -xv && mv ${ROS_STACK_NAME}-${ROS_STACK_VERSION} ${ROS_STACK_NAME})

install: ${ROS_DISTRO_DIR}/${ROS_STACK_NAME}
	./update_version.py debian/changelog.tmp > debian/changelog
	bash -c ". setup_deb.sh && ./gen_versioned_debs.py ${ROS_DISTRO_NAME} ${ROS_STACK_NAME}" >> ${SUBSTFILE}
	bash -c ". setup_deb.sh && env"
	bash -c ". setup_deb.sh && rosmake ${ROS_STACK_NAME} -V --skip-blacklist --status-rate=0"
	bash -c ". setup_deb.sh && rosmake ${ROS_STACK_NAME} -i -V --skip-blacklist --status-rate=0"
ifneq (${ROS_DISTRO_NAME}, cturtle)
	bash -c ". setup_deb.sh && ./purge_build.py ${ROS_DISTRO_DIR}"
endif
	rm -rf ${ROS_STACK_DIR}/${ROS_STACK_NAME}/*/build/CMakeFiles
	-python -mcompileall ${ROS_STACK_DIR}/${ROS_STACK_NAME}
	./fixrpath.py ${ROS_STACK_DIR}/${ROS_STACK_NAME} ${ROS_DISTRO_DIR} ${ROS_DISTRO_DIR_FINAL}
	./fixpc.py ${ROS_STACK_DIR}/${ROS_STACK_NAME} ${ROS_DISTRO_DIR} ${ROS_DISTRO_DIR_FINAL}

clean:

